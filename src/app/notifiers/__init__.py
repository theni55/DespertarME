"""Notifiers push + factory gated por configuración (D30 patrón, D40 para FCM).

`build_notifier()` decide en runtime qué notifier usar:
- Si `FCM_CREDENTIALS_PATH` o `FCM_CREDENTIALS_JSON` están configurados y
  `firebase-admin` se inicializa correctamente → `FcmNotifier` (push real).
- Si no → `DummyNotifier` (log-only). Así el MVP backend puede desplegarse sin
  Firebase y activarse después solo con variables de entorno.
"""

import logging

from app.config import settings
from app.notifiers.base import AlertPayload, PushNotifier, PushResult
from app.notifiers.dummy import DummyNotifier

logger = logging.getLogger(__name__)

__all__ = [
    "AlertPayload",
    "DummyNotifier",
    "PushNotifier",
    "PushResult",
    "build_notifier",
]


def build_notifier() -> PushNotifier:
    """Factory: FcmNotifier si hay credenciales, si no Dummy."""
    if not (settings.fcm_credentials_path or settings.fcm_credentials_json):
        logger.warning(
            "Notifier activo: DummyNotifier (log-only). "
            "Configura FCM_CREDENTIALS_PATH o FCM_CREDENTIALS_JSON para activar push reales."
        )
        return DummyNotifier()
    try:
        from app.notifiers.fcm import FcmNotifier

        notifier = FcmNotifier()
        logger.info("Notifier activo: FcmNotifier (push reales)")
        return notifier
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "FcmNotifier no se pudo inicializar (%s). Usando DummyNotifier fallback.", exc
        )
        return DummyNotifier()


# Singleton del notifier construido lazy (compartido por scheduler y endpoints
# que necesiten enviar un push puntual, como test-alarm).
_notifier_singleton: PushNotifier | None = None


def get_notifier() -> PushNotifier:
    """Devuelve el notifier singleton (lo crea en la primera llamada)."""
    global _notifier_singleton
    if _notifier_singleton is None:
        _notifier_singleton = build_notifier()
    return _notifier_singleton
