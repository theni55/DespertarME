"""Notifier de prueba (log-only).

No realiza envíos reales; registra el mensaje en log y devuelve éxito (o fallo
forzado por `fail_on_token` para tests). Útil para validar plomería sin Firebase.
"""

from __future__ import annotations

import logging
import uuid

from app.notifiers.base import AlertPayload, PushNotifier, PushResult

logger = logging.getLogger(__name__)


class DummyNotifier(PushNotifier):
    """Notifier que solo registra en log; simula éxito."""

    def __init__(self, *, fail_on_token: str | None = None) -> None:
        self._fail_on_token = fail_on_token

    async def send(self, payload: AlertPayload) -> PushResult:
        logger.info(
            "[DummyNotifier] push %s a device=%s token=%s: %s | bout=%s event=%s fighters=%s "
            "start=%s in_min=%s",
            payload.message_type,
            payload.device_id[:8],
            payload.fcm_token[:12],
            payload.event_name,
            payload.bout_id,
            payload.event_id,
            payload.fighters,
            payload.estimated_start_at,
            payload.minutes_until_start,
        )
        if self._fail_on_token and payload.fcm_token == self._fail_on_token:
            return PushResult(success=False, error="forced failure for testing")
        return PushResult(success=True, message_id=f"dummy-{uuid.uuid4().hex[:8]}")
