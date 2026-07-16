"""Notifier FCM (D40) usando `firebase-admin`.

Envía mensajes **data-only high-priority** (sin `notification` block) para que
Android los entregue al handler background de la app incluso con la app en
background/Doze. El cliente (`@reactnative-firebase/messaging` en Fase 7b)
reprograma la alarma local (`AlarmManager.setAlarmClock`) al recibir `update`,
y muestra una notificación informativa al recibir `started`/`cancelled`.

`fire` se usa solo desde `POST /api/devices/me/test-alarm`: el handler foreground
de la app arranca el `AlarmService` del spike para validar el sonido.

Gated por `FCM_CREDENTIALS_PATH` o `FCM_CREDENTIALS_JSON` (mismo patrón D30):
si faltan → `build_notifier()` devuelve `DummyNotifier`.
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from app.config import settings
from app.notifiers.base import AlertPayload, PushNotifier, PushResult

logger = logging.getLogger(__name__)

_CREDENTIALS_ADAPTER: TypeAdapter[dict[str, Any]] = TypeAdapter(dict[str, Any])


def _load_credentials() -> dict[str, Any] | None:
    """Carga el service account JSON desde path o env-var inline."""
    if settings.fcm_credentials_path:
        path = Path(settings.fcm_credentials_path)
        if not path.is_file():
            logger.warning("FCM_CREDENTIALS_PATH apunta a fichero inexistente: %s", path)
            return None
        return _CREDENTIALS_ADAPTER.validate_json(path.read_text(encoding="utf-8"))
    if settings.fcm_credentials_json:
        try:
            return _CREDENTIALS_ADAPTER.validate_json(settings.fcm_credentials_json)
        except Exception:
            logger.warning("FCM_CREDENTIALS_JSON no es JSON válido")
            return None
    return None


class FcmNotifier(PushNotifier):
    """Envía pushes FCM data-only high-priority vía firebase-admin."""

    def __init__(self, credentials: dict[str, Any] | None = None) -> None:
        try:
            import firebase_admin
            from firebase_admin import credentials as fb_credentials
            from firebase_admin import messaging
        except ImportError as exc:
            raise RuntimeError(
                "firebase-admin no instalado. Ejecuta: pip install firebase-admin>=6.5"
            ) from exc

        self._messaging = messaging
        creds = credentials or _load_credentials()
        if creds is None:
            raise RuntimeError(
                "FcmNotifier requiere FCM_CREDENTIALS_PATH o FCM_CREDENTIALS_JSON configurados."
            )
        cred_obj = fb_credentials.Certificate(creds)
        try:
            self._app = firebase_admin.get_app()
        except ValueError:
            self._app = firebase_admin.initialize_app(cred_obj, name="despertarme-fcm")
        logger.info("FcmNotifier inicializado con proyecto=%s", creds.get("project_id"))

    async def send(self, payload: AlertPayload) -> PushResult:
        """Envía un mensaje data-only high-priority al token FCM del device."""
        message = self._messaging.Message(
            data=payload.to_data(),
            token=payload.fcm_token,
            android=self._messaging.AndroidConfig(priority="high"),
        )
        start = time.monotonic()
        try:
            # SDK síncrono → asyncio.to_thread para no bloquear el event loop.
            msg_id = await asyncio.to_thread(self._messaging.send, message, False)
            return PushResult(
                success=True,
                message_id=str(msg_id),
                duration_seconds=time.monotonic() - start,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("FcmNotifier fallo enviando a token=%s: %s", payload.fcm_token[:12], exc)
            return PushResult(
                success=False,
                error=str(exc),
                duration_seconds=time.monotonic() - start,
            )
