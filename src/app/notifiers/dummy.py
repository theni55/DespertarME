"""Notifier de prueba (log-only).

No realiza llamadas reales; registra la alerta en log y devuelve éxito.
Útil para validar el flujo end-to-end en Fase 2b sin proveedor SIM (Fase 5).
"""

from __future__ import annotations

import logging
import uuid

from app.notifiers.base import AlertPayload, CallResult, VoiceNotifier

logger = logging.getLogger(__name__)


class DummyNotifier(VoiceNotifier):
    """Notifier que solo registra en log; simula éxito."""

    def __init__(self, *, fail_on_phone: str | None = None) -> None:
        self._fail_on_phone = fail_on_phone

    async def call(self, payload: AlertPayload) -> CallResult:
        logger.info(
            "[DummyNotifier] Llamada a %s: %s vs %s (%s) en %s — %d min",
            payload.phone,
            payload.red_name or "?",
            payload.blue_name or "?",
            payload.weight_class or "?",
            payload.event_name,
            payload.minutes_until_start,
        )
        if self._fail_on_phone and payload.phone == self._fail_on_phone:
            return CallResult(success=False, error="forced failure for testing")
        return CallResult(success=True, call_id=f"dummy-{uuid.uuid4().hex[:8]}")
