"""Resolver de atletas con caché (WS1 del MVP launch, D32).

Resuelve `athlete_id -> (nombre, foto)` siguiendo el `$ref` de ESPN. Como una
card de 14 combates implica ~28 atletas, cachea agresivamente:

1. **Redis** (TTL 7 días por defecto): compartida entre requests/procesos.
2. **Memoria** (dict TTL): fallback si Redis no está disponible y capa L1.

Los fallos de red al resolver un atleta NO propagan: se devuelve un
`ResolvedAthlete` con `name=None` para que la web degrade a "TBD".
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
from app.providers.base import Provider

logger = logging.getLogger(__name__)

_MAX_CONCURRENT_FETCHES = 4


@dataclass(frozen=True)
class ResolvedAthlete:
    """Datos mínimos de un atleta para web y mensaje de llamada."""

    id: str
    name: str | None = None
    headshot_url: str | None = None

    @property
    def display(self) -> str:
        return self.name or "TBD"


class AthleteResolver:
    """Resuelve atletas vía Provider con caché Redis + memoria."""

    def __init__(
        self,
        provider: Provider,
        *,
        redis_client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
        clock: Callable[[], float] | None = None,
        memory_cache: dict[str, tuple[float, ResolvedAthlete]] | None = None,
    ) -> None:
        self._provider = provider
        self._redis = redis_client
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.athlete_cache_ttl_seconds
        self._clock = clock or time.monotonic
        # Caché L1 en memoria: id -> (expira_en, ResolvedAthlete). Inyectable
        # para compartirla entre requests (module-level dict en la web).
        self._memory: dict[str, tuple[float, ResolvedAthlete]] = (
            memory_cache if memory_cache is not None else {}
        )

    def _redis_key(self, athlete_id: str) -> str:
        return f"athlete:{athlete_id}"

    # --- Caché ------------------------------------------------------------

    def _get_memory(self, athlete_id: str) -> ResolvedAthlete | None:
        entry = self._memory.get(athlete_id)
        if entry is None:
            return None
        expires_at, athlete = entry
        if self._clock() >= expires_at:
            del self._memory[athlete_id]
            return None
        return athlete

    def _set_memory(self, athlete: ResolvedAthlete) -> None:
        self._memory[athlete.id] = (self._clock() + self._ttl, athlete)

    async def _get_redis(self, athlete_id: str) -> ResolvedAthlete | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(self._redis_key(athlete_id))
        except Exception:
            logger.debug("Redis no disponible para caché de atletas (get)", exc_info=True)
            return None
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return ResolvedAthlete(
                id=data["id"], name=data.get("name"), headshot_url=data.get("headshot_url")
            )
        except (json.JSONDecodeError, KeyError):
            return None

    async def _set_redis(self, athlete: ResolvedAthlete) -> None:
        if self._redis is None:
            return
        payload = json.dumps(
            {"id": athlete.id, "name": athlete.name, "headshot_url": athlete.headshot_url},
            ensure_ascii=False,
        )
        try:
            await self._redis.set(self._redis_key(athlete.id), payload, ex=self._ttl)
        except Exception:
            logger.debug("Redis no disponible para caché de atletas (set)", exc_info=True)

    # --- Resolución -------------------------------------------------------

    async def resolve(self, athlete_id: str) -> ResolvedAthlete:
        """Resuelve un atleta. Nunca lanza: degrada a name=None."""
        cached = self._get_memory(athlete_id)
        if cached is not None:
            return cached

        from_redis = await self._get_redis(athlete_id)
        if from_redis is not None:
            self._set_memory(from_redis)
            return from_redis

        try:
            detail = await self._provider.get_athlete(athlete_id)
            resolved = ResolvedAthlete(
                id=athlete_id,
                name=detail.display_name or None,
                headshot_url=detail.headshot_url,
            )
        except Exception:
            logger.warning("No se pudo resolver el atleta %s", athlete_id)
            # No cachear el fallo: reintentar en el siguiente request.
            return ResolvedAthlete(id=athlete_id)

        self._set_memory(resolved)
        await self._set_redis(resolved)
        return resolved

    async def resolve_many(self, athlete_ids: Iterable[str]) -> dict[str, ResolvedAthlete]:
        """Resuelve varios atletas en paralelo (concurrencia limitada)."""
        unique_ids = list(dict.fromkeys(aid for aid in athlete_ids if aid))
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

        async def _bounded(aid: str) -> ResolvedAthlete:
            async with semaphore:
                return await self.resolve(aid)

        results = await asyncio.gather(*(_bounded(aid) for aid in unique_ids))
        return {athlete.id: athlete for athlete in results}
