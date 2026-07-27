"""Resolver de equipos NBA con cache (D58).

NBA competitors no traen `name` inline (a diferencia de tenis D49). El
`team $ref` apunta a `.../seasons/{year}/teams/{id}` que expone
`displayName` + `logos[]`. Como solo hay ~30 equipos NBA y apenas cambian
entre seasons, cacheamos agresivamente (TTL 30 dias por defecto).

Los fallos de red al resolver un equipo NO propagan: se devuelve un
`ResolvedTeam` con `name=None` para que la UI degrade a "TBD".
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import redis.asyncio as redis

from app.config import settings
from app.providers._cache_resolver import CacheResolver
from app.providers.espn_nba import EspnNbaProvider

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedTeam:
    """Datos minimos de un equipo NBA para UI y mensaje de alerta."""

    id: str
    name: str | None = None
    logo_url: str | None = None

    @property
    def display(self) -> str:
        return self.name or "TBD"


class TeamResolver(CacheResolver[ResolvedTeam]):
    """Resuelve equipos via `EspnNbaProvider.get_team` con cache Redis + memoria."""

    def __init__(
        self,
        provider: EspnNbaProvider,
        *,
        redis_client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
        clock: Callable[[], float] | None = None,
        memory_cache: dict[str, tuple[float, ResolvedTeam]] | None = None,
    ) -> None:
        super().__init__(
            redis_client=redis_client,
            ttl_seconds=ttl_seconds if ttl_seconds is not None else settings.team_cache_ttl_seconds,
            clock=clock,
            memory_cache=memory_cache,
        )
        self._provider = provider

    @property
    def _prefix(self) -> str:
        return "team"

    async def _fetch_one(self, team_id: str) -> ResolvedTeam:
        detail = await self._provider.get_team(team_id)
        return ResolvedTeam(
            id=team_id,
            name=detail.display_name or None,
            logo_url=detail.logo_url,
        )

    def _empty(self, entity_id: str) -> ResolvedTeam:
        return ResolvedTeam(id=entity_id)

    def _to_dict(self, entity: ResolvedTeam) -> dict[str, object]:
        return {
            "id": entity.id,
            "name": entity.name,
            "logo_url": entity.logo_url,
        }

    def _from_dict(self, data: dict[str, Any]) -> ResolvedTeam:
        return ResolvedTeam(
            id=str(data.get("id", "")),
            name=(data["name"] if isinstance(data.get("name"), str) else None),
            logo_url=(data["logo_url"] if isinstance(data.get("logo_url"), str) else None),
        )
