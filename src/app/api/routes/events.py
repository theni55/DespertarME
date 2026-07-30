"""Router de eventos (Fase 7a + Fase 8 multi-sport).

Expone dos endpoints consumidos por las pantallas Home/Eventos/EventDetail de
la app:

- `GET /api/events?sport=mma|tennis&league=atp|wta` → lista de proximos eventos.
- `GET /api/events/{id}?sport=mma|tennis&league=atp|wta` → tarjeta con bouts.

Multi-sport (D47): `sport` enruta al deporte, `league` a la liga/subclase
dentro del deporte (atp/wta para tenis, ignorado para mma). `previous_bout_id`
se delega a `Card.previous_bout()`.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    BoutAthleteOut,
    BoutOut,
    EventCardOut,
    EventSummaryOut,
)
from app.db.session import get_session
from app.domain.entities import Card
from app.providers.athletes import AthleteResolver
from app.providers.base import Provider
from app.providers.espn_nba import EspnNbaProvider
from app.providers.espn_tennis import _TOURNAMENT_DISPLAY_NAMES, EspnTennisProvider
from app.providers.espn_ufc import EspnUfcProvider
from app.providers.models import Bout as ProviderBout
from app.providers.models import Competitor as ProviderCompetitor
from app.providers.teams import TeamResolver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

EVENTS_LIST_TTL_SECONDS = 300
EVENTS_LIST_CACHE_KEY = "events:upcoming:{sport}:{league}"

_providers: dict[tuple[str, str], Provider] = {}
_resolver: AthleteResolver | None = None
_team_resolver: TeamResolver | None = None
_redis: Any = None


def _get_provider(sport: str = "mma", league: str = "") -> Provider:
    global _providers, _resolver, _team_resolver, _redis
    key = (sport, league)
    if key not in _providers:
        import redis.asyncio as aioredis

        from app.config import settings

        if sport == "mma":
            _providers[key] = EspnUfcProvider()
        elif sport == "tennis":
            _providers[key] = EspnTennisProvider(league=league or settings.espn_tennis_league)
        elif sport == "nba":
            _providers[key] = EspnNbaProvider(league=league or settings.espn_nba_league)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deporte no soportado: {sport}",
            )

        if _redis is None:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        if _resolver is None:
            _resolver = AthleteResolver(_providers[key], redis_client=_redis)
        if _team_resolver is None and sport == "nba":
            _team_resolver = TeamResolver(
                _providers[key],  # type: ignore[arg-type]
                redis_client=_redis,
            )
    return _providers[key]


async def close_events_resources() -> None:
    global _providers, _resolver, _team_resolver, _redis
    for provider in _providers.values():
        try:
            await provider.aclose()
        except Exception:
            logger.exception("Error cerrando provider")
    _providers = {}
    if _redis is not None:
        await _redis.aclose()
        _redis = None
    _resolver = None
    _team_resolver = None


def _parse_iso_z(raw: str) -> datetime:
    value = raw
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _previous_bout_id_map(bouts: list[ProviderBout], sport: str = "mma") -> dict[str, str | None]:
    """Map de bout_id -> previous_bout_id usando Card.previous_bout().

    Delega la logica de "cual es el combate anterior" a la capa de dominio
    en lugar de replicarla en la API (D47).
    """
    from app.domain.entities import Bout as DomainBout

    domain_bouts: list[DomainBout] = []
    for b in bouts:
        comp_date = b.date
        if comp_date.endswith("Z"):
            comp_date = comp_date[:-1] + "+00:00"
        domain_bouts.append(
            DomainBout(
                id=b.id,
                match_number=b.match_number,
                date=datetime.fromisoformat(comp_date),
                card_segment=b.card_segment.name if b.card_segment else None,
                weight_class=b.weight_class.text if b.weight_class else None,
                sport=sport,
                court=b.court.description if b.court else None,
                round_description=b.round.description if b.round else None,
            )
        )

    card = Card(event_id="", event_name="", bouts=domain_bouts, sport=sport)
    result: dict[str, str | None] = {}
    for dbout in domain_bouts:
        prev = card.previous_bout(dbout)
        result[dbout.id] = prev.id if prev else None
    return result


@router.get("", response_model=list[EventSummaryOut])
async def list_events(
    session: AsyncSession = Depends(get_session),
    include_past_hours: int = 0,
    sport: str = "mma",
    league: str = "",
) -> list[EventSummaryOut]:
    """Lista proximos eventos del deporte/liga indicados.

    `sport`: "mma" (default) o "tennis".
    `league`: "atp"|"wta" para tenis, ignorado para mma.
    """
    provider = _get_provider(sport, league)
    cutoff = datetime.now(UTC) - timedelta(hours=include_past_hours)
    cacheable = include_past_hours == 0
    cache_key = EVENTS_LIST_CACHE_KEY.format(sport=sport, league=league)

    raw_cache: str | None = None
    if cacheable and _redis is not None:
        try:
            raw_cache = await _redis.get(cache_key)
        except Exception:
            logger.debug("Redis caido en list_events; bypass cache")
    if raw_cache:
        import json

        try:
            cached = json.loads(raw_cache)
            return [EventSummaryOut(**item) for item in cached]
        except Exception:
            logger.warning("Cache events corrupta; ignorando")

    try:
        summaries = await provider.list_upcoming_events(min_date=cutoff)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider no disponible: {exc}",
        ) from exc

    out = [
        EventSummaryOut(id=s.id, name=s.name, date=_parse_iso_z(s.date), image_url=None)
        for s in summaries
    ]
    if cacheable and _redis is not None and out:
        import json

        try:
            payload = json.dumps(
                [
                    {"id": e.id, "name": e.name, "date": e.date.isoformat(), "image_url": None}
                    for e in out
                ]
            )
            await _redis.set(cache_key, payload, ex=EVENTS_LIST_TTL_SECONDS)
        except Exception:
            logger.debug("No se pudo escribir cache events")
    return out


@router.get("/{event_id}", response_model=EventCardOut)
async def get_event_detail(
    event_id: str,
    session: AsyncSession = Depends(get_session),
    sport: str = "mma",
    league: str = "",
) -> EventCardOut:
    """Tarjeta de un evento con bouts ordenados y `previous_bout_id` calculado.

    Multi-sport (D47): `previous_bout_id` se deriva via `Card.previous_bout()`
    segun el deporte (court+date para tenis, matchNumber+1 para MMA).
    """
    provider = _get_provider(sport, league)
    resolver = _resolver or AthleteResolver(provider)
    # Detectar sufijo _doubles para filtrar por modalidad (solo tenis).
    base_event_id = event_id
    doubles_only = False
    singles_only = False
    if sport == "tennis" and event_id.endswith("_doubles"):
        base_event_id = event_id[: -len("_doubles")]
        doubles_only = True
    elif sport == "tennis":
        singles_only = True

    try:
        event = await provider.get_event_card(base_event_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider no disponible: {exc}",
        ) from exc

    previous_map = _previous_bout_id_map(event.bouts, sport)

    # D49: tenis tiene nombres inline en competitor.name — no hace falta
    # resolver atletas via el endpoint /athletes/{id} (costoso: 126 llamadas
    # para 63 partidos, ~16s). Para MMA seguimos usando AthleteResolver.
    # D58: NBA usa TeamResolver (competitors llevan `team $ref`, no `athlete`).
    resolved: dict[str, Any] = {}
    resolved_teams: dict[str, Any] = {}
    if sport == "tennis":
        pass  # tenis: nombres inline, no resolver.
    elif sport == "nba":
        team_ids = [
            c.team.team_id
            for b in event.bouts
            for c in (b.red_corner, b.blue_corner)
            if c and c.team and c.team.team_id
        ]
        if _team_resolver is not None and team_ids:
            resolved_teams = await _team_resolver.resolve_many(team_ids)
    else:
        athlete_ids = [
            c.athlete.athlete_id
            for b in event.bouts
            for c in (b.red_corner, b.blue_corner)
            if c and c.athlete and c.athlete.athlete_id
        ]
        resolved = await resolver.resolve_many(athlete_ids)

    def _to_athlete_out(corner: ProviderCompetitor | None) -> BoutAthleteOut | None:
        if corner is None:
            return None
        # D49 tenis: nombre inline directo.
        if corner.name:
            return BoutAthleteOut(id=corner.id, name=corner.name)
        # MMA: athlete $ref.
        if corner.athlete is not None:
            aid = corner.athlete.athlete_id
            if not aid:
                return None
            found = resolved.get(aid)
            return BoutAthleteOut(
                id=aid,
                name=found.name if found else None,
                headshot_url=found.headshot_url if found else None,
            )
        # D58 NBA: team $ref → name + logo_url.
        if corner.team is not None:
            tid = corner.team.team_id
            if not tid:
                return None
            found = resolved_teams.get(tid)
            return BoutAthleteOut(
                id=tid,
                name=found.name if found else None,
                headshot_url=found.logo_url if found else None,
            )
        return None

    bouts_out: list[BoutOut] = []
    for b in event.bouts:
        red = b.red_corner
        blue = b.blue_corner

        # Saltar combates ya acabados (winner=true) — MMA + Tenis.
        if (red and red.winner) or (blue and blue.winner):
            continue

        # Tenis: saltar partidos cuyos jugadores aun no se conocen (TBD).
        if sport == "tennis":
            if red is None or blue is None:
                continue
            if (red.name or "").upper() == "TBD" or (blue.name or "").upper() == "TBD":
                continue
            # Filtrar por modalidad si se pidio solo doubles o singles.
            if doubles_only or singles_only:
                bout_type = (b.weight_class.text if b.weight_class else "") or ""
                if doubles_only and "Doubles" not in bout_type:
                    continue
                if singles_only and "Singles" not in bout_type:
                    continue

        bouts_out.append(
            BoutOut(
                id=b.id,
                match_number=b.match_number,
                date=_parse_iso_z(b.date),
                card_segment=b.card_segment.name if b.card_segment else None,
                weight_class=(
                    b.weight_class.text
                    if b.weight_class
                    else (b.round.description if b.round else None)
                ),
                periods=b.format.regulation.periods if b.format else 3,
                red=_to_athlete_out(b.red_corner),
                blue=_to_athlete_out(b.blue_corner),
                previous_bout_id=previous_map.get(b.id),
                court=b.court.description if b.court else None,
                sport=sport,
                round_description=b.round.description if b.round else None,
            )
        )

    # Nombre "comun" para tenis (mapping), manteniendo el de ESPN como fallback.
    display_name = event.name
    if sport == "tennis":
        tournament_id = base_event_id.split("-")[0]
        mapped = _TOURNAMENT_DISPLAY_NAMES.get((league or "atp", tournament_id), event.name)
        display_name = mapped

    return EventCardOut(
        id=event_id,
        name=display_name if not doubles_only else f"{display_name} Dobles",
        date=_parse_iso_z(event.date),
        image_url=None,
        bouts=bouts_out,
    )
