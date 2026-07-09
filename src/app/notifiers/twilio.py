"""Notifier real de llamadas con Twilio (Fase 5 / MVP launch, D30).

Realiza la llamada con TwiML inline (`<Say>` TTS en español), sin necesidad de
webhook público. El SDK de Twilio es síncrono → se ejecuta en un thread con
`asyncio.to_thread` para no bloquear el event loop.

Los reintentos (D17) los gestiona el Poller; aquí cada `call()` es un intento.
"""

from __future__ import annotations

import asyncio
import logging
from xml.sax.saxutils import escape

from twilio.rest import Client

from app.config import settings
from app.notifiers.base import AlertPayload, CallResult, VoiceNotifier

logger = logging.getLogger(__name__)


def _build_message(payload: AlertPayload) -> str:
    """Mensaje TTS en español para la llamada."""
    red = payload.red_name or "tu peleador"
    blue = payload.blue_name or "su rival"
    event = payload.event_name or "el evento"
    if payload.minutes_until_start > 0:
        timing = f"empieza en unos {payload.minutes_until_start} minutos"
    else:
        timing = "está a punto de empezar"
    return (
        f"Hola, te llamamos de Despertar M E. "
        f"El combate {red} contra {blue} de {event} {timing}. "
        f"¡No te lo pierdas!"
    )


def _build_twiml(message: str) -> str:
    # Repetimos el mensaje 2 veces: el usuario puede tardar en llevarse
    # el teléfono a la oreja tras descolgar.
    say = f'<Say language="es-ES">{escape(message)}</Say>'
    return f'<Response>{say}<Pause length="1"/>{say}</Response>'


class TwilioNotifier(VoiceNotifier):
    """Llamadas de voz reales vía Twilio (TwiML inline, sin webhook)."""

    def __init__(
        self,
        *,
        account_sid: str | None = None,
        auth_token: str | None = None,
        from_number: str | None = None,
        client: Client | None = None,
    ) -> None:
        self._from_number = from_number or settings.twilio_from_number
        self._client = client or Client(
            account_sid or settings.twilio_account_sid,
            auth_token or settings.twilio_auth_token,
        )

    async def call(self, payload: AlertPayload) -> CallResult:
        message = _build_message(payload)
        twiml = _build_twiml(message)
        try:
            # SDK síncrono → thread para no bloquear el event loop.
            call = await asyncio.to_thread(
                self._client.calls.create,
                to=payload.phone,
                from_=self._from_number,
                twiml=twiml,
            )
        except Exception as exc:
            logger.warning("Twilio call a %s falló: %s", payload.phone, exc)
            return CallResult(success=False, error=str(exc))
        logger.info("Twilio call creada: sid=%s to=%s", call.sid, payload.phone)
        return CallResult(success=True, call_id=call.sid)
