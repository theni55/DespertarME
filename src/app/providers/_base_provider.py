"""Clase base compartida para providers ESPN (refactor Sesion NBA).

Unifica el circuit breaker, backoff tenacity, lifecycle httpx y helpers HTTP
que estaban duplicados identicos en EspnUfcProvider, EspnTennisProvider y
EspnNbaProvider (~100 lineas cada uno).

Cada provider concreto solo implementa los 4 metodos abstractos de Provider +
sus helpers especificos de deporte (sintesis de quarters NBA, parsing de
event_id, etc.).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any, cast

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import settings
from app.providers.base import Provider

logger = logging.getLogger(__name__)


class CircuitBreakerOpenError(Exception):
    """El circuit breaker esta abierto; no se realizan requests."""


def _is_retryable(exc: BaseException) -> bool:
    """Predicate de tenacity: reintenta en 429/5xx y errores de transporte."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return isinstance(exc, httpx.TransportError)


class _EspnBaseProvider(Provider):
    """Base compartida con CB, tenacity y ciclo de vida httpx.

    Subclases deben sobreescribir los 4 metodos abstractos de Provider (o al
    menos los que usen: get_event_card, get_competition_status, get_athlete,
    list_upcoming_events).

    Constructor: acepta los mismos kwargs que los providers concretos. Cada
    subclase pasa el league default especifico via super().__init__(league=...).
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        league: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        cb_fails: int | None = None,
        cb_open_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._base_url = (base_url or settings.espn_base_url).rstrip("/")
        self._league = league or ""
        self._timeout = timeout if timeout is not None else settings.espn_timeout_seconds
        self._max_retries = max_retries if max_retries is not None else settings.espn_max_retries
        self._cb_fails = cb_fails if cb_fails is not None else settings.espn_circuit_breaker_fails
        self._cb_open_seconds = (
            cb_open_seconds
            if cb_open_seconds is not None
            else settings.espn_circuit_breaker_open_seconds
        )
        self._client = client or httpx.AsyncClient(timeout=self._timeout)
        self._owns_client = client is None
        self._clock = clock or time.monotonic
        self._consecutive_failures = 0
        self._open_until: float = 0.0

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> _EspnBaseProvider:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # --- Circuit breaker -------------------------------------------------

    def _check_circuit(self) -> None:
        if self._clock() < self._open_until:
            raise CircuitBreakerOpenError(
                f"Circuit breaker abierto hasta {self._open_until:.1f}s "
                f"(fails={self._cb_fails}, open={self._cb_open_seconds}s)"
            )

    def _on_success(self) -> None:
        if self._consecutive_failures or self._open_until:
            logger.debug("Circuit breaker reset tras exito")
        self._consecutive_failures = 0
        self._open_until = 0.0

    def _on_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._cb_fails:
            self._open_until = self._clock() + self._cb_open_seconds
            self._consecutive_failures = 0
            logger.warning(
                "Circuit breaker ABIERTO por %ss tras %s fallos consecutivos",
                self._cb_open_seconds,
                self._cb_fails,
            )

    @property
    def is_circuit_open(self) -> bool:
        return self._clock() < self._open_until

    # --- HTTP con tenacity + circuit breaker -----------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def _request(self, url: str) -> dict[str, Any]:
        """Request con circuit breaker delante y tenacity (backoff) dentro.

        E5: el circuit breaker solo cuenta fallos *retryables* (429/5xx,
        TransportError). Los 4xx NO abren el circuito (DoS trivial evitado).
        """
        self._check_circuit()
        try:
            data = await self._request_with_retry(url)
        except Exception as exc:
            if _is_retryable(exc):
                self._on_failure()
            raise
        self._on_success()
        return data

    async def _request_with_retry(self, url: str) -> dict[str, Any]:
        """Reintenta con backoff exponencial + jitter (D20) sobre 429/5xx."""
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential_jitter(initial=1, max=60),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )
        async for attempt in retrying:
            with attempt:
                response = await self._client.get(url)
                response.raise_for_status()
                return cast(dict[str, Any], response.json())
        raise RuntimeError("retry loop exited without a result")
