"""Provider de ESPN Core API para UFC/MMA (D9, D13, D20).

Endpoints (verificados en vivo, Sesion 2):
- `GET /sports/mma/leagues/{league}/events?seasontype=2` -> lista de eventos
  (solo `$ref`; el id se parsea y se pide el detalle).
- `GET /sports/mma/leagues/{league}/events/{id}` -> tarjeta completa (14 combates).
- `GET /sports/mma/leagues/{league}/events/{id}/competitions/{cId}/status`
  -> `{clock, period, type:{state:"pre"|"in"|"post", completed}}`.

Resiliencia (D20): heredada de `_EspnBaseProvider` — backoff exponencial con
jitter + circuit breaker manual.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.providers._base_provider import _EspnBaseProvider
from app.providers.models import AthleteDetail, CompetitionStatus, Event, EventSummary

logger = logging.getLogger(__name__)

_EVENT_ID_RE = re.compile(r"/events/(\d+)")


def _event_id_from_ref(ref: str) -> str | None:
    """Extrae el `eventId` de un `$ref` de ESPN (URL completa).

    Ej: `http://.../events/600059148?lang=en&region=us` -> `600059148`.
    """
    if not ref:
        return None
    path = urlparse(ref).path
    m = _EVENT_ID_RE.search(path)
    return m.group(1) if m else None


def _parse_event_date(raw: str) -> datetime:
    """Parsea una fecha ISO de ESPN (ej. `2026-07-11T21:00Z`) a datetime UTC."""
    value = raw
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


class EspnUfcProvider(_EspnBaseProvider):
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
        super().__init__(
            base_url=base_url,
            league=league or settings.espn_league,
            timeout=timeout,
            max_retries=max_retries,
            cb_fails=cb_fails,
            cb_open_seconds=cb_open_seconds,
            client=client,
            clock=clock,
        )

    # --- Provider ABC ----------------------------------------------------

    async def list_upcoming_events(
        self, *, min_date: datetime | None = None, max_concurrent: int = 4
    ) -> Sequence[EventSummary]:
        """Lista los eventos proximos (no pasados) de la liga.

        Fase 7a:
        - `min_date` filtra eventos cuya fecha sea anterior (default: ahora UTC).
        - Los N+1 fetches de detalle se paralelizan con `asyncio.gather` limitado
          a `max_concurrent` (default 4).
        """
        list_url = self._url(f"/sports/mma/leagues/{self._league}/events?seasontype=2")
        data = await self._request(list_url)
        ids: list[str] = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                ids.append(eid)

        sem = asyncio.Semaphore(max_concurrent)

        async def _fetch_summary(eid: str) -> EventSummary | None:
            url = self._url(f"/sports/mma/leagues/{self._league}/events/{eid}")
            async with sem:
                try:
                    ev_data = await self._request(url)
                except Exception:
                    logger.warning("No se pudo cargar resumen del evento %s", eid)
                    return None
            ev_status = (ev_data.get("status") or {}).get("type") or {}
            if ev_status.get("state") == "post":
                return None
            return EventSummary(
                id=ev_data["id"],
                name=ev_data.get("name", ""),
                date=ev_data.get("date", ""),
            )

        raw_summaries = await asyncio.gather(*(_fetch_summary(eid) for eid in ids))
        summaries = [s for s in raw_summaries if s is not None]

        cutoff = min_date or datetime.now(UTC)
        upcoming: list[EventSummary] = []
        for s in summaries:
            try:
                ev_dt = _parse_event_date(s.date)
            except ValueError:
                logger.warning("Fecha invalida en evento %s: %s", s.id, s.date)
                continue
            if ev_dt >= cutoff:
                upcoming.append(s)
            else:
                # Evento con fecha pasada que NO es 'post' (el _fetch_summary
                # ya los filtra). Mantenerlo: es un evento en 'in' que sigue
                # en curso y debe ser visible en Buscar/Home.
                upcoming.append(s)
        upcoming.sort(key=lambda x: x.date)
        return upcoming

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

    async def get_athlete(self, athlete_id: str) -> AthleteDetail:
        url = self._url(f"/sports/mma/athletes/{athlete_id}")
        data = await self._request(url)
        return AthleteDetail.model_validate(data)
