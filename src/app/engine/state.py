"""Gestión de estado e idempotencia con Redis (D16).

Clave Redis `alert:{subscription_id}:{bout_id}:{status_when_fired}` con TTL
configurable (default 7200 s). Si la clave ya existe, la alerta ya se disparó
para ese estado → no se repite.

Defensa en profundidad: además del Redis, hay UNIQUE constraint en `alert_log`
`(subscription_id, bout_id, fired_at_hour)` que evita duplicados en BD.
"""

from __future__ import annotations

import logging

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class AlertState:
    """Maneja la idempotencia de alertas en Redis."""

    def __init__(
        self,
        client: redis.Redis | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        self._client = client or redis.from_url(settings.redis_url, decode_responses=True)
        self._owns_client = client is None
        self._ttl = (
            ttl_seconds if ttl_seconds is not None else settings.alert_idempotency_ttl_seconds
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _key(self, subscription_id: str, bout_id: str, status: str) -> str:
        return f"alert:{subscription_id}:{bout_id}:{status}"

    async def try_mark_fired(self, subscription_id: str, bout_id: str, status: str) -> bool:
        """Marca una alerta como disparada. Devuelve True si es la primera vez.

        Si devuelve False, la alerta ya se disparó para ese estado → idempotente.
        Usa SETNX + EXPIRE atómico vía `SET key 1 NX EX ttl`.
        """
        key = self._key(subscription_id, bout_id, status)
        result = await self._client.set(key, "1", nx=True, ex=self._ttl)
        if result:
            logger.debug("Alerta marcada como disparada: %s", key)
            return True
        logger.debug("Alerta ya disparada (skip): %s", key)
        return False

    async def was_fired(self, subscription_id: str, bout_id: str, status: str) -> bool:
        key = self._key(subscription_id, bout_id, status)
        return bool(await self._client.exists(key))

    async def reset(self, subscription_id: str, bout_id: str, status: str) -> None:
        """Borra la marca (útil para tests o reintentos manuales)."""
        key = self._key(subscription_id, bout_id, status)
        await self._client.delete(key)
