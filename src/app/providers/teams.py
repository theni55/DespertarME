"""Resolver de equipos NBA con cache (D58).

NBA competitors no traen `name` inline (a diferencia de tenis D49). El
`team $ref` apunta a `.../seasons/{year}/teams/{id}` que expone
`displayName` + `logos[]`. Como solo hay ~30 equipos NBA y apenas cambian
entre seasons, cacheamos agresivamente (TTL 30 dias por defecto):

1. **Redis** (TTL configurable): compartida entre requests/procesos.
2. **Memoria** (dict TTL): fallback si Redis no esta disponible y capa L1.

Los fallos de red al resolver un equipo NO propagan: se devuelve un
`ResolvedTeam` con `name=None` para que la UI degrade a "TBD".
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

import redis.asyncio as redis

from app.config import settings
from app.providers.espn_nba import EspnNbaProvider

logger = logging.getLogger(__name__)

_MAX_CONCURRENT_FETCHES = 4


@dataclass(frozen=True)
class ResolvedTeam:
    """Datos minimos de un equipo NBA para UI y mensaje de alerta."""

    id: str
    name: str | None = None
    logo_url: str | None = None

    @property
    def display(self) -> str:
        return self.name or "TBD"


class TeamResolver:
    """Resuelve equipos via `EspnNbaProvider.get_team` con cache Redis + memoria.

    Mismo patron que `AthleteResolver` (D32) pero para equipos NBA.
    """

    def __init__(
        self,
        provider: EspnNbaProvider,
        *,
        redis_client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
        clock: Callable[[], float] | None = None,
        memory_cache: dict[str, tuple[float, ResolvedTeam]] | None = None,
    ) -> None:
        self._provider = provider
        self._redis = redis_client
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.team_cache_ttl_seconds
        self._clock = clock or time.monotonic
        self._memory: dict[str, tuple[float, ResolvedTeam]] = (
            memory_cache if memory_cache is not None else {}
        )

    def _redis_key(self, team_id: str) -> str:
        return f"team:{team_id}"

    # --- Cache ------------------------------------------------------------

    def _get_memory(self, team_id: str) -> ResolvedTeam | None:
        entry = self._memory.get(team_id)
        if entry is None:
            return None
        expires_at, team = entry
        if self._clock() >= expires_at:
            del self._memory[team_id]
            return None
        return team

    def _set_memory(self, team: ResolvedTeam) -> None:
        self._memory[team.id] = (self._clock() + self._ttl, team)

    async def _get_redis(self, team_id: str) -> ResolvedTeam | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(self._redis_key(team_id))
        except Exception:
            logger.debug("Redis no disponible para cache de equipos (get)", exc_info=True)
            return None
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return ResolvedTeam(id=data["id"], name=data.get("name"), logo_url=data.get("logo_url"))
        except (json.JSONDecodeError, KeyError):
            return None

    async def _set_redis(self, team: ResolvedTeam) -> None:
        if self._redis is None:
            return
        payload = json.dumps(
            {"id": team.id, "name": team.name, "logo_url": team.logo_url},
            ensure_ascii=False,
        )
        try:
            await self._redis.set(self._redis_key(team.id), payload, ex=self._ttl)
        except Exception:
            logger.debug("Redis no disponible para cache de equipos (set)", exc_info=True)

    # --- Resolucion -------------------------------------------------------

    async def resolve(self, team_id: str) -> ResolvedTeam:
        """Resuelve un equipo. Nunca lanza: degrada a name=None."""
        cached = self._get_memory(team_id)
        if cached is not None:
            return cached

        from_redis = await self._get_redis(team_id)
        if from_redis is not None:
            self._set_memory(from_redis)
            return from_redis

        try:
            detail = await self._provider.get_team(team_id)
            resolved = ResolvedTeam(
                id=team_id,
                name=detail.display_name or None,
                logo_url=detail.logo_url,
            )
        except Exception:
            logger.warning("No se pudo resolver el equipo NBA %s", team_id)
            return ResolvedTeam(id=team_id)

        self._set_memory(resolved)
        await self._set_redis(resolved)
        return resolved

    async def resolve_many(self, team_ids: Iterable[str]) -> dict[str, ResolvedTeam]:
        """Resuelve varios equipos en paralelo (concurrencia limitada)."""
        unique_ids = list(dict.fromkeys(tid for tid in team_ids if tid))
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

        async def _bounded(tid: str) -> ResolvedTeam:
            async with semaphore:
                return await self.resolve(tid)

        results = await asyncio.gather(*(_bounded(tid) for tid in unique_ids))
        return {team.id: team for team in results}
