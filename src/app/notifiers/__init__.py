"""Notifiers de llamadas + factory gated por configuración (D30).

`build_notifier()` decide en runtime qué notifier usar:
- Si `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` y `TWILIO_FROM_NUMBER` están
  configurados → `TwilioNotifier` (llamadas reales).
- Si falta cualquiera → `DummyNotifier` (log-only). Así el MVP puede desplegarse
  sin cuenta Twilio y activarse después solo con variables de entorno.
"""

import logging

from app.config import settings
from app.notifiers.base import AlertPayload, CallResult, VoiceNotifier
from app.notifiers.dummy import DummyNotifier

logger = logging.getLogger(__name__)

__all__ = [
    "AlertPayload",
    "CallResult",
    "DummyNotifier",
    "VoiceNotifier",
    "build_notifier",
]


def build_notifier() -> VoiceNotifier:
    """Factory: TwilioNotifier si hay credenciales completas, si no Dummy."""
    if settings.twilio_account_sid and settings.twilio_auth_token and settings.twilio_from_number:
        # Import diferido: no cargar el SDK de Twilio si no se usa.
        from app.notifiers.twilio import TwilioNotifier

        logger.info("Notifier activo: TwilioNotifier (llamadas reales)")
        return TwilioNotifier()
    logger.warning(
        "Notifier activo: DummyNotifier (log-only). "
        "Configura TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN/TWILIO_FROM_NUMBER "
        "para activar llamadas reales."
    )
    return DummyNotifier()
