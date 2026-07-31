"""Gestión de estado e idempotencia con Redis (D16 + E2).

Dos usos:

1. **Idempotencia de alerta disparada** (D16): clave
   `alert:{subscription_id}:{bout_id}:{status}` con TTL configurable (default
   7200 s). Si la clave ya existe, la alerta ya se disparó para ese estado.
   Defensa en profundidad: además del Redis hay UNIQUE `(subscription_id,
   bout_id, fired_at_epoch_hour)` en `alert_log` (E6).

2. **Anclaje de transición in→post** (E2): clave
   `transition:{event_id}:{bout_id}` guarda el timestamp UTC de la primera
   observación del combate previo en estado `post`. El EstimatorEngine usa
   ese momento fijo para calcular `start_at = observed_at + buffer` en vez de
   `now + buffer` (que se deslizaba al infinito en cada poll). TTL largo (24 h)
   porque una transición `in→post` solo ocurre una vez por combate.
"""

from __future__ import annotations

import logging
from datetime import datetime

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)

# TTL largo para la transición in→post: solo ocurre una vez por combate, pero
# queremos que expire eventualmente para no acumular basura entre eventos.
TRANSITION_TTL_SECONDS = 24 * 3600


class AlertState:
    """Maneja la idempotencia de alertas y el anclaje de transiciones en Redis."""

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

    def _transition_key(self, event_id: str, bout_id: str) -> str:
        return f"transition:{event_id}:{bout_id}"

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

    async def remember_transition(
        self, event_id: str, bout_id: str, observed_at: datetime
    ) -> datetime:
        """Ancla la transición in→post en `observed_at` si es la primera vez.

        Devuelve el timestamp anclado (el que quedó persistido, ya sea el que
        pasamos o uno anterior si ya existía). Idempotente: llamadas
        repetidas con la misma clave no sobreescriben.
        """
        key = self._transition_key(event_id, bout_id)
        iso = observed_at.isoformat()
        # NX: solo set si no existe. Devuelve True si se seteó, None si ya existía.
        set_result = await self._client.set(key, iso, nx=True, ex=TRANSITION_TTL_SECONDS)
        if set_result:
            logger.debug("Transición anclada %s → %s", key, iso)
            return observed_at
        existing = await self._client.get(key)
        if existing is None:
            # Expiró entre el set y el get (race muy estrecho); re-intentamos.
            await self._client.set(key, iso, ex=TRANSITION_TTL_SECONDS)
            return observed_at
        return datetime.fromisoformat(_as_str(existing))

    async def get_transition(self, event_id: str, bout_id: str) -> datetime | None:
        """Devuelve el timestamp anclado de la transición in→post, o None."""
        key = self._transition_key(event_id, bout_id)
        existing = await self._client.get(key)
        if existing is None:
            return None
        return datetime.fromisoformat(_as_str(existing))

    def _estimate_key(self, subscription_id: str, bout_id: str) -> str:
        return f"estimate:{subscription_id}:{bout_id}"

    async def get_last_estimate(self, subscription_id: str, bout_id: str) -> datetime | None:
        """Devuelve la última estimación pusheada (D40 push on-change), o None."""
        key = self._estimate_key(subscription_id, bout_id)
        existing = await self._client.get(key)
        if existing is None:
            return None
        return datetime.fromisoformat(_as_str(existing))

    async def set_last_estimate(
        self, subscription_id: str, bout_id: str, start_at: datetime
    ) -> None:
        """Persiste la última estimación pusheada. TTL = idempotencia de alerta."""
        key = self._estimate_key(subscription_id, bout_id)
        await self._client.set(key, start_at.isoformat(), ex=self._ttl)


def _as_str(value: bytes | str) -> str:
    """Coerce bytes|str de Redis a str (fakeredis a veces devuelve bytes)."""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value
