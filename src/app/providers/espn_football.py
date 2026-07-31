"""Provider de ESPN Core API para Futbol (D65).

Modelo "1 partido = 1 bout" (MVP): cada partido de futbol se expone como
una Card de 1 Bout con 2 competidores (home/away) via `team $ref`. Sin
sintesis de mitades (eso sera una futura ampliacion tipo NBA).

Resiliencia (D20): heredada de `_EspnBaseProvider`.

Endpoints (verificados en vivo, Sesion 28):
- `GET /sports/soccer/leagues/{league}/events` -> lista de partidos.
- `GET /sports/soccer/leagues/{league}/events/{id}` -> partido con 1 competition.
- `GET /sports/soccer/leagues/{league}/events/{id}/competitions/{cId}/status`
  -> estado del partido (`clock`, `period`, `type.state`). `competition_id == event_id`.
- `GET /sports/soccer/leagues/{league}/seasons/{year}/teams/{id}` -> team
  detail (`displayName`, `logos[]`).

Ligas soportadas (D65): `settings.football_leagues`. Por ahora son las
top 7 europeas: esp.1, eng.1, ita.1, ger.1, fra.1, uefa.champions,
uefa.europa. Ampliable anadiendo slugs a la lista de settings.
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


class EspnFootballProvider(_EspnBaseProvider):
    """Provider concreto para ESPN Core API (Futbol).

    MVP (D65): 1 partido = 1 bout, sin sintesis de mitades. Los equipos se
    resuelven via `get_team` + `TeamResolver` (mismo patron que NBA).
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
        super().__init__(
            base_url=base_url,
            league=league or settings.espn_football_league,
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
        list_url = self._url(f"/sports/soccer/leagues/{self._league}/events")
        data = await self._request(list_url)
        ids: list[str] = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                ids.append(eid)

        sem = asyncio.Semaphore(max_concurrent)

        async def _fetch_summary(eid: str) -> EventSummary | None:
            url = self._url(f"/sports/soccer/leagues/{self._league}/events/{eid}")
            async with sem:
                try:
                    ev_data = await self._request(url)
                except Exception:
                    logger.warning("No se pudo cargar resumen del partido %s", eid)
                    return None

            status = ev_data.get("status")
            if status is not None and isinstance(status, dict):
                status_type = status.get("type") or {}
                if status_type.get("state") == "post":
                    return None

            return EventSummary(
                id=str(ev_data["id"]),
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
        """Devuelve la card de UN partido con 1 competition (MVP: 1 bout).

        La competition tiene 2 competitors (home/away) con `team $ref`.
        Los equipos se resuelven via `TeamResolver` en la capa de API/poller.

        Remapea `order` 0/1 (home/away ESPN) -> 1/2 (red/blue corner)
        para mantener la convencion de los modelos compartidos (D65).
        """
        url = self._url(f"/sports/soccer/leagues/{self._league}/events/{event_id}")
        data = await self._request(url)
        data = self._remap_competitor_order(data)
        return Event.model_validate(data)

    @staticmethod
    def _remap_competitor_order(data: dict[str, Any]) -> dict[str, Any]:
        """Remapea order 0/1 (home/away ESPN) -> 1/2 (red/blue corner).

        La convencion interna de `Bout.red_corner`/`blue_corner` busca
        `order==1` (red) y `order==2` (blue). ESPN football envia `order:0`
        (home) y `order:1` (away). Los mapeamos para que coincidan con la
        convencion MMA/NBA (rojo=local, azul=visitante).
        """
        competitions = data.get("competitions") or []
        for comp in competitions:
            competitors = comp.get("competitors") or []
            for c in competitors:
                o = c.get("order", 0)
                c["order"] = 1 if o == 0 else 2
        return data

    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        """Estado en vivo del partido.

        Para football, `competition_id == event_id` (mismo patron que NBA).
        El status expone `clock` (segundos transcurridos del tiempo actual),
        `period` (0=pre, 1=1st half, 2=2nd half), `type.state` (pre/in/post).
        """
        cid = competition_id or event_id
        url = self._url(
            f"/sports/soccer/leagues/{self._league}/events/{event_id}" f"/competitions/{cid}/status"
        )
        data = await self._request(url)
        return CompetitionStatus.model_validate(data)

    async def get_athlete(self, athlete_id: str) -> Any:  # noqa: ANN401
        """Football no usa `athlete $ref`; los equipos se resuelven via
        `get_team` y `TeamResolver` (D65)."""
        raise NotImplementedError("Futbol usa get_team, no get_athlete")

    async def get_team(self, team_id: str) -> TeamDetail:
        """Detalle de un equipo de futbol. Hace probing de years para encontrar
        el equipo en cualquier season activa (current, current+1, current-1)."""
        years = [datetime.now(UTC).year, datetime.now(UTC).year + 1, datetime.now(UTC).year - 1]
        last_exc: Exception | None = None
        for year in years:
            url = self._url(f"/sports/soccer/leagues/{self._league}/seasons/{year}/teams/{team_id}")
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
