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

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    BoutAthleteOut,
    BoutOut,
    EventCardOut,
    EventSummaryOut,
)
from app.config import settings
from app.db.session import get_session
from app.domain.entities import Card
from app.providers._visibility import bout_has_real_competitors
from app.providers.athletes import AthleteResolver
from app.providers.base import Provider
from app.providers.espn_football import EspnFootballProvider
from app.providers.espn_nba import EspnNbaProvider
from app.providers.espn_nfl import EspnNflProvider
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
_resolvers: dict[str, AthleteResolver] = {}
_team_resolvers: dict[str, TeamResolver] = {}
_redis: Any = None
_shared_client: httpx.AsyncClient | None = None
_SHARED_CLIENT_LIMITS = httpx.Limits(max_connections=50, max_keepalive_connections=20)


def get_shared_http_client() -> httpx.AsyncClient:
    """Devuelve un singleton httpx.AsyncClient compartido entre todos los providers
    del router events y el scheduler. Un solo pool de conexiones para evitar OOM
    en Railway (512 MB free tier) cuando HomeViewModel dispara 6 fetches
    paralelos que instancian ~6 providers cada uno con su propio cliente.
    """
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.espn_timeout_seconds),
            limits=_SHARED_CLIENT_LIMITS,
        )
    return _shared_client


def _get_provider(sport: str = "mma", league: str = "") -> Provider:
    global _providers, _resolvers, _team_resolvers, _redis
    key = (sport, league)
    if key not in _providers:
        import redis.asyncio as aioredis

        http_client = get_shared_http_client()

        if sport == "mma":
            _providers[key] = EspnUfcProvider(client=http_client)
        elif sport == "tennis":
            _providers[key] = EspnTennisProvider(league=league or settings.espn_tennis_league, client=http_client)
        elif sport == "nba":
            _providers[key] = EspnNbaProvider(league=league or settings.espn_nba_league, client=http_client)
        elif sport == "nfl":
            _providers[key] = EspnNflProvider(league=league or settings.espn_nfl_league, client=http_client)
        elif sport == "football":
            _providers[key] = EspnFootballProvider(league=league or settings.espn_football_league, client=http_client)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deporte no soportado: {sport}",
            )

        if _redis is None:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        if sport not in _resolvers:
            _resolvers[sport] = AthleteResolver(_providers[key], redis_client=_redis, sport=sport)
        if sport == "nba" and "nba" not in _team_resolvers:
            _team_resolvers["nba"] = TeamResolver(
                _providers[key],
                redis_client=_redis,
            )
        if sport == "nfl" and "nfl" not in _team_resolvers:
            _team_resolvers["nfl"] = TeamResolver(
                _providers[key],
                redis_client=_redis,
            )
        if sport == "football" and league not in _team_resolvers:
            _team_resolvers[league] = TeamResolver(
                _providers[key],
                redis_client=_redis,
            )
    return _providers[key]


async def close_events_resources() -> None:
    global _providers, _resolvers, _team_resolvers, _redis, _shared_client
    for provider in _providers.values():
        try:
            await provider.aclose()
        except Exception:
            logger.exception("Error cerrando provider")
    _providers = {}
    if _redis is not None:
        await _redis.aclose()
        _redis = None
    _resolvers = {}
    _team_resolvers = {}
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None


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
    fresh_key = EVENTS_LIST_CACHE_KEY.format(sport=sport, league=league)
    stale_key = f"{fresh_key}:stale"
    stale_ttl = 3600  # 1 h — fallback si ESPN falla

    raw_cache: str | None = None
    if cacheable and _redis is not None:
        try:
            raw_cache = await _redis.get(fresh_key)
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
        # Si el provider falla, intentar servir cache stale.
        if cacheable and _redis is not None:
            try:
                stale_raw = await _redis.get(stale_key)
            except Exception:
                stale_raw = None
            if stale_raw:
                import json

                try:
                    logger.warning("Provider caido (%s); sirviendo cache stale", exc)
                    cached = json.loads(stale_raw)
                    return [EventSummaryOut(**item) for item in cached]
                except Exception:
                    logger.warning("Cache stale corrupta")
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
            await _redis.set(fresh_key, payload, ex=EVENTS_LIST_TTL_SECONDS)
            await _redis.set(stale_key, payload, ex=stale_ttl)
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
    resolver = _resolvers.get(sport) or AthleteResolver(provider, redis_client=_redis, sport=sport)
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

    # Si el evento ya empezo (fecha pasada), detectar combates en curso
    # y terminados. Los 'post' se filtran; los 'in' se muestran con badge
    # LIVE (sin boton de aviso). Para eventos futuros (fecha >= now), todos
    # los combates estan en 'pre' -> 0 llamadas.
    post_bout_ids: set[str] = set()
    in_bout_ids: set[str] = set()
    ev_date = _parse_iso_z(event.date)
    if ev_date < datetime.now(UTC):
        sem = asyncio.Semaphore(4)

        async def _fetch_status(bout: Any) -> tuple[str, str | None]:
            rid = bout.red_corner
            bid_blue = bout.blue_corner
            if (rid and rid.winner) or (bid_blue and bid_blue.winner):
                return (bout.id, "post")
            async with sem:
                try:
                    st = await provider.get_competition_status(base_event_id, bout.id)
                    return (bout.id, st.type.state)
                except Exception:
                    logger.debug("No se pudo obtener status del bout %s", bout.id)
                    return (bout.id, None)

        statuses = await asyncio.gather(*[_fetch_status(b) for b in event.bouts])
        post_bout_ids = {bid for bid, state in statuses if state == "post"}
        in_bout_ids = {bid for bid, state in statuses if state == "in"}

    # D58: NBA usa TeamResolver (competitors llevan `team $ref`, no `athlete`).
    resolved: dict[str, Any] = {}
    resolved_teams: dict[str, Any] = {}
    if sport == "tennis":
        athlete_ids = [
            c.athlete.athlete_id
            for b in event.bouts
            for c in (b.red_corner, b.blue_corner)
            if c and c.athlete and c.athlete.athlete_id
        ]
        if athlete_ids:
            resolved = await resolver.resolve_many(athlete_ids)
    elif sport == "nba":
        team_ids = [
            c.team.team_id
            for b in event.bouts
            for c in (b.red_corner, b.blue_corner)
            if c and c.team and c.team.team_id
        ]
        nba_tr = _team_resolvers.get("nba")
        if nba_tr is not None and team_ids:
            resolved_teams = await nba_tr.resolve_many(team_ids)
    elif sport == "nfl":
        team_ids = [
            c.team.team_id
            for b in event.bouts
            for c in (b.red_corner, b.blue_corner)
            if c and c.team and c.team.team_id
        ]
        nfl_tr = _team_resolvers.get("nfl")
        if nfl_tr is not None and team_ids:
            resolved_teams = await nfl_tr.resolve_many(team_ids)
    elif sport == "football":
        team_ids = [
            c.team.team_id
            for b in event.bouts
            for c in (b.red_corner, b.blue_corner)
            if c and c.team and c.team.team_id
        ]
        foot_tr = _team_resolvers.get(league or "")
        if foot_tr is not None and team_ids:
            resolved_teams = await foot_tr.resolve_many(team_ids)
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
        # D49 tenis: nombre inline directo, headshot via athlete $ref.
        if corner.name:
            headshot = None
            if corner.athlete and corner.athlete.athlete_id:
                found = resolved.get(corner.athlete.athlete_id)
                if found:
                    headshot = found.headshot_url
            return BoutAthleteOut(id=corner.id, name=corner.name, headshot_url=headshot)
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

        # Universal: saltar bouts sin competidores reales (TBD/Bye/None).
        if not bout_has_real_competitors(
            red.name if red else None,
            str(red.id) if red else None,
            blue.name if blue else None,
            str(blue.id) if blue else None,
        ):
            continue

        # Saltar combates ya acabados (winner=true) — todos los deportes.
        if (red and red.winner) or (blue and blue.winner):
            continue

        # Saltar combates en estado 'post' (terminados sin winner declarado).
        if b.id in post_bout_ids:
            continue

        # Determinar status del bout (pre/in).
        bout_status: str | None = None
        if b.id in in_bout_ids:
            bout_status = "in"

        # Tenis: filtrar por modalidad si se pidio solo doubles o singles.
        if sport == "tennis" and (doubles_only or singles_only):
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
                status=bout_status,
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
