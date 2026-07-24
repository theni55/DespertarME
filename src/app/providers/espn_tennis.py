"""Provider de ESPN Core API para Tenis ATP/WTA (D46).

Endpoints (verificados en vivo, Sesion 23):
- `GET /sports/tennis/leagues/{league}/events?seasontype=2` → lista de torneos.
- `GET /sports/tennis/leagues/{league}/events/{id}` → torneo completo.
- `GET /sports/tennis/leagues/{league}/events/{id}/competitions/{cId}/status`
  → `{period, type:{state:"pre"|"in"|"post", completed}}` (sin `clock`).

Resiliencia (D20): misma estrategia que EspnUfcProvider — backoff exponencial
con jitter + circuit breaker manual. Codigo compartido via herencia de la logica
de CB + tenacity de la clase base comun _EspnBaseProvider.

Diferencias clave con MMA (D49):
- Nombres de jugadores inline en `competitors[].name` → no requiere AthleteResolver.
- Sin `matchNumber` → orden por `date` dentro de cada `court`.
- Sin `clock` en status → solo `period` (numero de set).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
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
from app.providers.espn_ufc import CircuitBreakerOpenError, _is_retryable
from app.providers.models import AthleteDetail, CompetitionStatus, Event, EventSummary

logger = logging.getLogger(__name__)

_EVENT_ID_RE = re.compile(r"/events/(\d+-\d+|\d+)")


def _event_id_from_ref(ref: str) -> str | None:
    if not ref:
        return None
    path = urlparse(ref).path
    m = _EVENT_ID_RE.search(path)
    return m.group(1) if m else None


def _parse_event_date(raw: str) -> datetime:
    value = raw
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


class EspnTennisProvider(Provider):
    """Provider concreto para ESPN Core API (Tenis ATP/WTA)."""

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
        self._league = league or settings.espn_tennis_league
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

    async def __aenter__(self) -> EspnTennisProvider:
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

    async def list_upcoming_events(
        self, *, min_date: datetime | None = None, max_concurrent: int = 4
    ) -> Sequence[EventSummary]:
        list_url = self._url(f"/sports/tennis/leagues/{self._league}/events?seasontype=2")
        data = await self._request(list_url)
        ids: list[str] = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                ids.append(eid)

        sem = asyncio.Semaphore(max_concurrent)

        async def _fetch_summary(eid: str) -> EventSummary | None:
            url = self._url(f"/sports/tennis/leagues/{self._league}/events/{eid}")
            async with sem:
                try:
                    ev_data = await self._request(url)
                except Exception:
                    logger.warning("No se pudo cargar resumen del torneo %s", eid)
                    return None
            return EventSummary(
                id=ev_data["id"],
                name=ev_data.get("name", ""),
                date=ev_data.get("date", ""),
            )

        raw_summaries = await asyncio.gather(*(_fetch_summary(eid) for eid in ids))
        summaries = [s for s in raw_summaries if s is not None]

        cutoff = min_date or datetime.now(UTC)
        # Tenis: torneos duran 1-2 semanas. Incluir torneos en curso
        # aunque su fecha de inicio ya paso (ej. Generali Open empezo
        # 18-jul pero hoy 24-jul sigue activo con semifinales).
        min_cutoff = datetime.now(UTC) - timedelta(days=14)
        if cutoff > min_cutoff:
            cutoff = min_cutoff
        upcoming: list[EventSummary] = []
        for s in summaries:
            try:
                ev_dt = _parse_event_date(s.date)
            except ValueError:
                logger.warning("Fecha invalida en torneo %s: %s", s.id, s.date)
                continue
            if ev_dt >= cutoff:
                upcoming.append(s)
        upcoming.sort(key=lambda x: x.date)
        return upcoming

    async def get_event_card(self, event_id: str) -> Event:
        url = self._url(f"/sports/tennis/leagues/{self._league}/events/{event_id}")
        data = await self._request(url)
        return Event.model_validate(data)

    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        url = self._url(
            f"/sports/tennis/leagues/{self._league}/events/{event_id}"
            f"/competitions/{competition_id}/status"
        )
        data = await self._request(url)
        return CompetitionStatus.model_validate(data)

    async def get_athlete(self, athlete_id: str) -> AthleteDetail:
        url = self._url(f"/sports/tennis/athletes/{athlete_id}")
        data = await self._request(url)
        return AthleteDetail.model_validate(data)
