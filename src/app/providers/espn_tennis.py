"""Provider de ESPN Core API para Tenis ATP/WTA (D46).

Endpoints (verificados en vivo, Sesion 23):
- `GET /sports/tennis/leagues/{league}/events?seasontype=2` -> lista de torneos.
- `GET /sports/tennis/leagues/{league}/events/{id}` -> torneo completo.
- `GET /sports/tennis/leagues/{league}/events/{id}/competitions/{cId}/status`
  -> `{period, type:{state:"pre"|"in"|"post", completed}}` (sin `clock`).

Resiliencia (D20): heredada de `_EspnBaseProvider`.

Diferencias clave con MMA (D49):
- Nombres de jugadores inline en `competitors[].name` -> no requiere AthleteResolver.
- Sin `matchNumber` -> orden por `date` dentro de cada `court`.
- Sin `clock` en status -> solo `period` (numero de set).
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.providers._base_provider import _EspnBaseProvider
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


class EspnTennisProvider(_EspnBaseProvider):
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
        super().__init__(
            base_url=base_url,
            league=league or settings.espn_tennis_league,
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
