"""Provider de ESPN Core API para NBA (D56).

Modelo "Bout = Cuarto" (D56): cada partido NBA se sintetiza como una Card
de 4 Bouts Q1-Q4. ESPN expone SOLO el estado global del partido (state +
period + clock); no expone estado pre/in/post por cuartos. Ergo el provider
deriva el estado de cada cuarto comparando el `period` global vs el quarter
objetivo.

Resiliencia (D20): heredada de `_EspnBaseProvider`.

Endpoints (verificados en vivo, Sesion NBA):
- `GET /sports/basketball/leagues/{league}/events?seasontype=2` -> lista de partidos.
- `GET /sports/basketball/leagues/{league}/events/{id}` -> partido con 1 competition.
- `GET /sports/basketball/leagues/{league}/events/{id}/competitions/{cId}/status`
  -> estado global del partido (`clock`, `period`, `type.state`). Para NBA,
  `competition_id == event_id`.
- `GET /sports/basketball/leagues/nba/seasons/{year}/teams/{id}` -> team
  detail (`displayName`, `logos[]`).
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import settings
from app.providers._base_provider import _EspnBaseProvider
from app.providers.models import CompetitionStatus, Event, EventSummary, TeamDetail

logger = logging.getLogger(__name__)

_EVENT_ID_RE = re.compile(r"/events/(\d+)")
_QUARTER_RE = re.compile(r"_q(\d+)$")

# Cache en memoria del status global por event_id: (timestamp, status_dict).
# TTL corto (3s) para dedupe llamadas dentro del mismo poll cycle.
_STATUS_CACHE_TTL = 3.0


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


class EspnNbaProvider(_EspnBaseProvider):
    """Provider concreto para ESPN Core API (NBA)."""

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
            league=league or settings.espn_nba_league,
            timeout=timeout,
            max_retries=max_retries,
            cb_fails=cb_fails,
            cb_open_seconds=cb_open_seconds,
            client=client,
            clock=clock,
        )
        self._status_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    # --- Provider ABC ----------------------------------------------------

    async def list_upcoming_events(
        self, *, min_date: datetime | None = None, max_concurrent: int = 4
    ) -> Sequence[EventSummary]:
        list_url = self._url(f"/sports/basketball/leagues/{self._league}/events?seasontype=2")
        data = await self._request(list_url)
        ids: list[str] = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                ids.append(eid)

        sem = asyncio.Semaphore(max_concurrent)

        async def _fetch_summary(eid: str) -> EventSummary | None:
            url = self._url(f"/sports/basketball/leagues/{self._league}/events/{eid}")
            async with sem:
                try:
                    ev_data = await self._request(url)
                except Exception:
                    logger.warning("No se pudo cargar resumen del partido %s", eid)
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
                logger.warning("Fecha invalida en partido %s: %s", s.id, s.date)
                continue
            if ev_dt >= cutoff:
                upcoming.append(s)
        upcoming.sort(key=lambda x: x.date)
        return upcoming

    async def get_event_card(self, event_id: str) -> Event:
        """Sintetiza un Event NBA con 4 competitions Q1-Q4 (D56).

        NBA tiene 1 solo `competition` por evento (1 partido = 1 competition).
        Remapeamos `order` 0/1 (home/away) -> 1/2 (red/blue corner) y creamos
        4 competitions sinteticas, una por cuarto, preservando teams y metadata.
        `Bout.id = "{eventId}_q{N}"`, `matchNumber = N`.
        """
        url = self._url(f"/sports/basketball/leagues/{self._league}/events/{event_id}")
        data = await self._request(url)
        return self._synthesize_quarter_card(event_id, data)

    @staticmethod
    def _synthesize_quarter_card(event_id: str, data: dict[str, Any]) -> Event:
        competitions = data.get("competitions") or []
        if not competitions:
            return Event.model_validate(data)
        real_comp = competitions[0]
        real_competitors = real_comp.get("competitors") or []
        remapped_competitors = [
            {
                **c,
                "order": 1 if c.get("order") == 0 else 2,
            }
            for c in real_competitors
        ]
        regulation = (real_comp.get("format") or {}).get("regulation") or {}
        clock_per_quarter = regulation.get("clock", 720.0)
        type_obj = real_comp.get("type")
        synthetic_competitions: list[dict[str, Any]] = []
        for q in range(1, 5):
            quarter_comp = {
                "id": f"{event_id}_q{q}",
                "matchNumber": q,
                "date": data.get("date", ""),
                "type": type_obj,
                "cardSegment": {"name": "Regulation", "description": "Regular season quarter"},
                "format": {
                    "regulation": {"periods": 1, "clock": clock_per_quarter},
                },
                "competitors": remapped_competitors,
            }
            synthetic_competitions.append(quarter_comp)
        synthetic_data = {**data, "competitions": synthetic_competitions}
        return Event.model_validate(synthetic_data)

    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        """Deriva el status de UN cuartel especifico a partir del status global."""
        m = _QUARTER_RE.search(competition_id or "")
        quarter_n = int(m.group(1)) if m else 0
        global_status = await self._fetch_global_status_cached(event_id)
        return self._derive_quarter_status(quarter_n, global_status)

    async def _fetch_global_status_cached(self, event_id: str) -> dict[str, Any]:
        """Fetch con cache en memoria de 3 s para evitar duplicar dentro del poll."""
        now_mono = self._clock()
        cached = self._status_cache.get(event_id)
        if cached is not None and cached[0] > now_mono:
            return cached[1]
        url = self._url(
            f"/sports/basketball/leagues/{self._league}/events/{event_id}"
            f"/competitions/{event_id}/status"
        )
        data = await self._request(url)
        self._status_cache[event_id] = (now_mono + _STATUS_CACHE_TTL, data)
        return data

    @staticmethod
    def _derive_quarter_status(
        quarter_n: int, global_status_data: dict[str, Any]
    ) -> CompetitionStatus:
        """Traduce el status global del juego a un status sintetico del quarter N."""
        g_state = (global_status_data.get("type") or {}).get("state", "pre")
        g_period = int(global_status_data.get("period", 0) or 0)

        if quarter_n == 0:
            return CompetitionStatus.model_validate(global_status_data)

        def _synth(state: str, *, completed: bool) -> CompetitionStatus:
            return CompetitionStatus.model_validate(
                {
                    "clock": 0.0,
                    "displayClock": "0.0",
                    "period": quarter_n,
                    "type": {
                        "state": state,
                        "completed": completed,
                        "description": "Scheduled" if state == "pre" else "Final",
                        "shortDetail": "TBD" if state == "pre" else "Final",
                    },
                }
            )

        if g_period == 0:
            return _synth("pre", completed=False)
        if quarter_n < g_period:
            return _synth("post", completed=True)
        if quarter_n > g_period:
            return _synth("pre", completed=False)
        if g_state == "pre":
            return _synth("pre", completed=False)
        return CompetitionStatus.model_validate(global_status_data)

    async def get_athlete(self, athlete_id: str) -> Any:  # noqa: ANN401
        """NBA no usa `athlete $ref`; los nombres se resuelven via `get_team`
        y `TeamResolver`. Mantenemos el metodo por compatibilidad con el ABC
        pero lanza NotImplementedError si alguien lo llama por error."""
        raise NotImplementedError("NBA usa get_team, no get_athlete")

    async def get_team(self, team_id: str) -> TeamDetail:
        """Detalle de un equipo NBA. Hace probing de years para encontrar el
        equipo en cualquier season activa (current, current+1, current-1)."""
        years = [datetime.now(UTC).year, datetime.now(UTC).year + 1, datetime.now(UTC).year - 1]
        last_exc: Exception | None = None
        for year in years:
            url = self._url(
                f"/sports/basketball/leagues/{self._league}/seasons/{year}/teams/{team_id}"
            )
            try:
                data = await self._request(url)
                return TeamDetail.model_validate(data)
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 404:
                    continue
                raise
            except Exception as exc:
                last_exc = exc
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"No se pudo resolver el equipo {team_id} en ninguna season")
