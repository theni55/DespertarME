"""Resolver de atletas con cache (WS1 del MVP launch, D32).

Resuelve `athlete_id -> (nombre, foto)` siguiendo el `$ref` de ESPN. Como una
card de 14 combates implica ~28 atletas, cachea agresivamente via Redis +
memoria L1 (logica compartida heredada de `CacheResolver`).

Los fallos de red al resolver un atleta NO propagan: se devuelve un
`ResolvedAthlete` con `name=None` para que la web degrade a "TBD".
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis

from app.providers._cache_resolver import CacheResolver
from app.providers.base import Provider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedAthlete:
    """Datos minimos de un atleta para web y mensaje de llamada."""

    id: str
    name: str | None = None
    headshot_url: str | None = None

    @property
    def display(self) -> str:
        return self.name or "TBD"


class AthleteResolver(CacheResolver[ResolvedAthlete]):
    """Resuelve atletas via Provider con cache Redis + memoria."""

    def __init__(
        self,
        provider: Provider,
        *,
        redis_client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
        clock: Callable[[], float] | None = None,
        memory_cache: dict[str, tuple[float, ResolvedAthlete]] | None = None,
        sport: str = "mma",
    ) -> None:
        super().__init__(
            redis_client=redis_client,
            ttl_seconds=ttl_seconds,
            clock=clock,
            memory_cache=memory_cache,
        )
        self._provider = provider
        self._sport = sport

    @property
    def _prefix(self) -> str:
        return "athlete"

    async def _fetch_one(self, athlete_id: str) -> ResolvedAthlete:
        detail = await self._provider.get_athlete(athlete_id)
        headshot_url = detail.headshot_url
        if self._sport != "mma" and detail.headshot is None:
            headshot_url = None
        return ResolvedAthlete(
            id=athlete_id,
            name=detail.display_name or None,
            headshot_url=headshot_url,
        )

    def _empty(self, entity_id: str) -> ResolvedAthlete:
        return ResolvedAthlete(id=entity_id)

    def _to_dict(self, entity: ResolvedAthlete) -> dict[str, object]:
        return {
            "id": entity.id,
            "name": entity.name,
            "headshot_url": entity.headshot_url,
        }

    def _from_dict(self, data: dict[str, Any]) -> ResolvedAthlete:
        return ResolvedAthlete(
            id=str(data.get("id", "")),
            name=(data["name"] if isinstance(data.get("name"), str) else None),
            headshot_url=(
                data["headshot_url"] if isinstance(data.get("headshot_url"), str) else None
            ),
        )
