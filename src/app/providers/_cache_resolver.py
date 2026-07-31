"""Cache generico Redis + memoria para entidades resueltas bajo demanda.

Extraido de `AthleteResolver` y `TeamResolver` (refactor Sesion NBA) que
compartian ~120 lineas identicas cambiando solo el key_prefix de Redis y
la funcion de fetch.

Cada subclase sobreescribe:
- `_prefix`: prefijo de clave Redis ("athlete", "team", ...).
- `_fetch_one(entity_id) -> T`: fetch real via provider (1 llamada de red).
- `_to_dict(T) -> dict`: serializacion para Redis.
- `_from_dict(dict) -> T`: deserializacion desde Redis/memoria.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any, Generic, TypeVar

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_CONCURRENT_FETCHES = 4

T = TypeVar("T")


class CacheResolver(ABC, Generic[T]):  # noqa: UP046
    """Cache generico con Redis + memoria L1 para entidades resueltas bajo demanda.

    Parametrizado por el tipo `T` que representa la entidad resuelta. Cada
    subclase define el key_prefix, la funcion de fetch y la serializacion.

    Nunca lanza excepciones de red: degrada a `_empty(entity_id) -> T` sin
    cachear el fallo.
    """

    def __init__(
        self,
        *,
        redis_client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
        clock: Callable[[], float] | None = None,
        memory_cache: dict[str, tuple[float, T]] | None = None,
    ) -> None:
        self._redis = redis_client
        self._ttl = ttl_seconds if ttl_seconds is not None else settings.athlete_cache_ttl_seconds
        self._clock = clock or time.monotonic
        self._memory: dict[str, tuple[float, T]] = memory_cache if memory_cache is not None else {}

    # --- Subclases debe sobreescribir -----------------------------------

    @property
    @abstractmethod
    def _prefix(self) -> str:
        """Prefijo de clave Redis (ej. "athlete", "team")."""
        ...

    @abstractmethod
    async def _fetch_one(self, entity_id: str) -> T:
        """Fetch real de un id (1 llamada de red). Devuelve la entidad resuelta."""
        ...

    @abstractmethod
    def _empty(self, entity_id: str) -> T:
        """Entidad vacia para degradar cuando el fetch falla (sin cachear)."""
        ...

    def _to_dict(self, entity: T) -> dict[str, object]:
        """Serializa la entidad para Redis. Default: usa atributos comunes."""
        return {
            "id": getattr(entity, "id", ""),
            "name": getattr(entity, "name", None),
            "image_url": getattr(entity, "image_url", None)
            or getattr(entity, "headshot_url", None)
            or getattr(entity, "logo_url", None),
        }

    def _from_dict(self, data: dict[str, Any]) -> T:
        """Deserializa desde Redis. Default: construct via kwargs."""
        return self._empty(str(data.get("id", "")))

    # --- Cache ------------------------------------------------------------

    def _redis_key(self, entity_id: str) -> str:
        return f"{self._prefix}:{entity_id}"

    def _get_memory(self, entity_id: str) -> T | None:
        entry = self._memory.get(entity_id)
        if entry is None:
            return None
        expires_at, entity = entry
        if self._clock() >= expires_at:
            del self._memory[entity_id]
            return None
        return entity

    def _set_memory(self, entity: T) -> None:
        eid = str(getattr(entity, "id", ""))
        self._memory[eid] = (self._clock() + self._ttl, entity)

    async def _get_redis(self, entity_id: str) -> T | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(self._redis_key(entity_id))
        except Exception:
            logger.debug("Redis no disponible para cache de %s (get)", self._prefix, exc_info=True)
            return None
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return self._from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    async def _set_redis(self, entity: T) -> None:
        if self._redis is None:
            return
        payload = json.dumps(self._to_dict(entity), ensure_ascii=False)
        try:
            eid = str(getattr(entity, "id", ""))
            await self._redis.set(self._redis_key(eid), payload, ex=self._ttl)
        except Exception:
            logger.debug("Redis no disponible para cache de %s (set)", self._prefix, exc_info=True)

    # --- Resolucion -------------------------------------------------------

    async def resolve(self, entity_id: str) -> T:
        """Resuelve una entidad. Nunca lanza: degrada a `_empty()`."""
        cached = self._get_memory(entity_id)
        if cached is not None:
            return cached

        from_redis = await self._get_redis(entity_id)
        if from_redis is not None:
            self._set_memory(from_redis)
            return from_redis

        try:
            entity = await self._fetch_one(entity_id)
        except Exception:
            logger.warning("No se pudo resolver entidad %s:%s", self._prefix, entity_id)
            return self._empty(entity_id)

        self._set_memory(entity)
        await self._set_redis(entity)
        return entity

    async def resolve_many(self, entity_ids: Iterable[str]) -> dict[str, T]:
        """Resuelve varias entidades en paralelo (concurrencia limitada)."""
        unique_ids = list(dict.fromkeys(eid for eid in entity_ids if eid))
        semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)

        async def _bounded(eid: str) -> T:
            async with semaphore:
                return await self.resolve(eid)

        results = await asyncio.gather(*(_bounded(eid) for eid in unique_ids))
        return {str(getattr(r, "id", "")): r for r in results}
