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
from app.providers.espn_tennis import EspnTennisProvider
from app.providers.espn_ufc import EspnUfcProvider
from app.providers.models import Bout as ProviderBout
from app.providers.models import Competitor as ProviderCompetitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

EVENTS_LIST_TTL_SECONDS = 300
EVENTS_LIST_CACHE_KEY = "events:upcoming:{sport}:{league}"

_providers: dict[tuple[str, str], Provider] = {}
_resolver: AthleteResolver | None = None
_redis: Any = None


def _get_provider(sport: str = "mma", league: str = "") -> Provider:
    global _providers, _resolver, _redis
    key = (sport, league)
    if key not in _providers:
        import redis.asyncio as aioredis

        from app.config import settings

        if sport == "mma":
            _providers[key] = EspnUfcProvider()
        elif sport == "tennis":
            _providers[key] = EspnTennisProvider(league=league or settings.espn_tennis_league)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deporte no soportado: {sport}",
            )

        if _redis is None:
            _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        if _resolver is None:
            _resolver = AthleteResolver(_providers[key], redis_client=_redis)
    return _providers[key]


async def close_events_resources() -> None:
    global _providers, _resolver, _redis
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
    try:
        event = await provider.get_event_card(event_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider no disponible: {exc}",
        ) from exc

    previous_map = _previous_bout_id_map(event.bouts, sport)

    # D49: tenis tiene nombres inline en competitor.name — no hace falta
    # resolver atletas via el endpoint /athletes/{id} (costoso: 126 llamadas
    # para 63 partidos, ~16s). Para MMA seguimos usando AthleteResolver.
    if sport != "tennis":
        athlete_ids = [
            c.athlete.athlete_id
            for b in event.bouts
            for c in (b.red_corner, b.blue_corner)
            if c and c.athlete and c.athlete.athlete_id
        ]
        resolved = await resolver.resolve_many(athlete_ids)
    else:
        resolved = {}

    def _to_athlete_out(corner: ProviderCompetitor | None) -> BoutAthleteOut | None:
        if corner is None or corner.athlete is None:
            if corner and corner.name:
                return BoutAthleteOut(id=corner.id, name=corner.name)
            return None
        aid = corner.athlete.athlete_id
        name = corner.name
        if not aid and not name:
            return None
        found = resolved.get(aid) if aid else None
        return BoutAthleteOut(
            id=aid or corner.id or "",
            name=name or (found.name if found else None),
            headshot_url=found.headshot_url if found else None,
        )

    bouts_out: list[BoutOut] = []
    for b in event.bouts:
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

    return EventCardOut(
        id=event.id,
        name=event.name,
        date=_parse_iso_z(event.date),
        image_url=None,
        bouts=bouts_out,
    )
