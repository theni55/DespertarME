"""Router de eventos (Fase 7a).

Expone dos endpoints consumidos por las pantallas Home/Eventos/EventDetail de
la app:

- `GET /api/events` → lista de próximos UFC (filtro por fecha + caché Redis).
- `GET /api/events/{id}` → tarjeta con bouts ordenados, fotos/nombres vía
  `AthleteResolver`, y `previous_bout_id` calculado server-side (E4: el cliente
  no lo manda; el backend lo deriva de la card fresca en cada request porque
  UFC reordena la card el día del evento).
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
from app.providers.athletes import AthleteResolver
from app.providers.espn_ufc import EspnUfcProvider
from app.providers.models import Competitor as ProviderCompetitor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/events", tags=["events"])

# TTL corto para la caché de la lista de eventos: la lista apenas cambia día a
# día, pero si se añade un evento nuevo queremos verlo en ~5 min.
EVENTS_LIST_TTL_SECONDS = 300
EVENTS_LIST_CACHE_KEY = "events:upcoming:ufc"

# Provider + resolver singletons a nivel de módulo (perezoso) para no acoplar
# la API a `scheduler.py`. El scheduler mantiene el suyo propio para el poller.
_provider: EspnUfcProvider | None = None
_resolver: AthleteResolver | None = None
_redis: Any = None  # redis.asyncio.Redis | None


def _get_provider() -> EspnUfcProvider:
    global _provider, _resolver, _redis
    if _provider is None:
        import redis.asyncio as aioredis

        from app.config import settings

        _provider = EspnUfcProvider()
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
        _resolver = AthleteResolver(_provider, redis_client=_redis)
    return _provider


async def close_events_resources() -> None:
    """Cerrar httpx client + redis al apagar la app (lifespan)."""
    global _provider, _resolver, _redis
    if _provider is not None:
        await _provider.aclose()
        _provider = None
    if _redis is not None:
        await _redis.aclose()
        _redis = None
    _resolver = None


def _parse_iso_z(raw: str) -> datetime:
    value = raw
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


@router.get("", response_model=list[EventSummaryOut])
async def list_events(
    session: AsyncSession = Depends(get_session),  # noqa: ARG001 - no usado pero parte del contrato
    include_past_hours: int = 0,
) -> list[EventSummaryOut]:
    """Lista próximos eventos UFC (caché Redis 5 min).

    `include_past_hours`: opcional (query), incluye eventos que terminaron hace
    menos de N horas (útil para ver resultados recientes). Default 0 = solo futuros.
    """
    provider = _get_provider()
    cutoff = datetime.now(UTC) - timedelta(hours=include_past_hours)
    # Intentamos caché
    raw_cache: str | None = None
    if _redis is not None:
        try:
            raw_cache = await _redis.get(EVENTS_LIST_CACHE_KEY)
        except Exception:
            logger.debug("Redis caído en list_events; bypass caché")
    if raw_cache:
        import json

        try:
            cached = json.loads(raw_cache)
            return [EventSummaryOut(**item) for item in cached]
        except Exception:
            logger.warning("Caché events corrupta; ignorando")

    try:
        summaries = await provider.list_upcoming_events(min_date=cutoff)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider ESPN no disponible: {exc}",
        ) from exc

    out = [
        EventSummaryOut(id=s.id, name=s.name, date=_parse_iso_z(s.date), image_url=None)
        for s in summaries
    ]
    # Guardar en caché (best-effort)
    if _redis is not None and out:
        import json

        try:
            payload = json.dumps(
                [
                    {"id": e.id, "name": e.name, "date": e.date.isoformat(), "image_url": None}
                    for e in out
                ]
            )
            await _redis.set(EVENTS_LIST_CACHE_KEY, payload, ex=EVENTS_LIST_TTL_SECONDS)
        except Exception:
            logger.debug("No se pudo escribir caché events")
    return out


@router.get("/{event_id}", response_model=EventCardOut)
async def get_event_detail(
    event_id: str,
    session: AsyncSession = Depends(get_session),  # noqa: ARG001
) -> EventCardOut:
    """Tarjeta de un evento con bouts ordenados y `previous_bout_id` calculado.

    `previous_bout_id` se deriva del vecino de Mayor matchNumber (E4): el
    cliente no lo manda porque UFC reordena la card el día del evento.
    """
    provider = _get_provider()
    resolver = _resolver or AthleteResolver(provider)
    try:
        event = await provider.get_event_card(event_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Provider ESPN no disponible: {exc}",
        ) from exc

    athlete_ids = [
        c.athlete.athlete_id
        for b in event.bouts
        for c in (b.red_corner, b.blue_corner)
        if c and c.athlete and c.athlete.athlete_id
    ]
    resolved = await resolver.resolve_many(athlete_ids)

    def _to_athlete_out(corner: ProviderCompetitor | None) -> BoutAthleteOut | None:
        if corner is None or corner.athlete is None:
            return None
        aid = corner.athlete.athlete_id
        if not aid:
            return None
        found = resolved.get(aid)
        return BoutAthleteOut(
            id=aid,
            name=found.name if found else None,
            headshot_url=found.headshot_url if found else None,
        )

    # E4: mapear matchNumber → bout_id para derivar previous_bout_id.
    match_to_id: dict[int, str] = {b.match_number: b.id for b in event.bouts}

    bouts_out: list[BoutOut] = []
    for b in event.bouts:
        prev_match = b.match_number + 1
        bouts_out.append(
            BoutOut(
                id=b.id,
                match_number=b.match_number,
                date=_parse_iso_z(b.date),
                card_segment=b.card_segment.name if b.card_segment else None,
                weight_class=b.weight_class.text if b.weight_class else None,
                periods=b.format.regulation.periods if b.format else 3,
                red=_to_athlete_out(b.red_corner),
                blue=_to_athlete_out(b.blue_corner),
                previous_bout_id=match_to_id.get(prev_match),
            )
        )

    return EventCardOut(
        id=event.id,
        name=event.name,
        date=_parse_iso_z(event.date),
        image_url=None,
        bouts=bouts_out,
    )
