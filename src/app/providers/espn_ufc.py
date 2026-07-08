"""Provider de ESPN Core API para UFC/MMA (D9, D13, D20).

Endpoints (verificados en vivo, Sesión 2):
- `GET /sports/mma/leagues/{league}/events?seasontype=2` → lista de eventos
  (solo `$ref`; el id se parsea y se pide el detalle).
- `GET /sports/mma/leagues/{league}/events/{id}` → tarjeta completa (14 combates).
- `GET /sports/mma/leagues/{league}/events/{id}/competitions/{cId}/status`
  → `{clock, period, type:{state:"pre"|"in"|"post", completed}}`.

Resiliencia (D20):
- Backoff exponencial con jitter (1→60 s cap) sobre 429/5xx y errores de
  transporte, vía `tenacity`.
- Circuit breaker manual: N fallos consecutivos (cada uno tras reintentos)
  abren el circuito durante `open_seconds`. Mientras está abierto, toda
  request lanza `CircuitBreakerOpen` sin tocar la red.

El circuit breaker usa un `clock` inyectable (default `time.monotonic`) para
facilitar tests con reloj fake.
"""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Sequence
from typing import Any, cast
from urllib.parse import urlparse

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import settings
from app.providers.base import Provider
from app.providers.models import CompetitionStatus, Event, EventSummary

logger = logging.getLogger(__name__)

_EVENT_ID_RE = re.compile(r"/events/(\d+)")


class CircuitBreakerOpenError(Exception):
    """El circuit breaker está abierto; no se realizan requests."""


def _is_retryable(exc: BaseException) -> bool:
    """Predicate de tenacity: reintenta en 429/5xx y errores de transporte."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return status == 429 or status >= 500
    return isinstance(exc, httpx.TransportError)


def _event_id_from_ref(ref: str) -> str | None:
    """Extrae el `eventId` de un `$ref` de ESPN (URL completa).

    Ej: `http://.../events/600059148?lang=en&region=us` → `600059148`.
    """
    if not ref:
        return None
    path = urlparse(ref).path
    m = _EVENT_ID_RE.search(path)
    return m.group(1) if m else None


class EspnUfcProvider(Provider):
    """Provider concreto para ESPN Core API (UFC)."""

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
        self._league = league or settings.espn_league
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

    async def __aenter__(self) -> EspnUfcProvider:
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
            logger.debug("Circuit breaker reset tras éxito")
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
        """Request con circuit breaker delante y tenacity (backoff) dentro."""
        self._check_circuit()
        try:
            data = await self._request_with_retry(url)
        except Exception:
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

    # --- Contrato Provider (base.py) -------------------------------------

    async def list_upcoming_events(self) -> Sequence[EventSummary]:
        list_url = self._url(f"/sports/mma/leagues/{self._league}/events?seasontype=2")
        data = await self._request(list_url)
        ids: list[str] = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                ids.append(eid)
        summaries: list[EventSummary] = []
        for eid in ids:
            ev_data = await self._request(
                self._url(f"/sports/mma/leagues/{self._league}/events/{eid}")
            )
            summaries.append(
                EventSummary(
                    id=ev_data["id"],
                    name=ev_data.get("name", ""),
                    date=ev_data.get("date", ""),
                )
            )
        return summaries

    async def get_event_card(self, event_id: str) -> Event:
        url = self._url(f"/sports/mma/leagues/{self._league}/events/{event_id}")
        data = await self._request(url)
        return Event.model_validate(data)

    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        url = self._url(
            f"/sports/mma/leagues/{self._league}/events/{event_id}"
            f"/competitions/{competition_id}/status"
        )
        data = await self._request(url)
        return CompetitionStatus.model_validate(data)
