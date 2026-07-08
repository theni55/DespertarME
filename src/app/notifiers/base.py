"""Interfaz del notificador de llamadas (D7, D23).

Cada proveedor de llamadas (Twilio en Fase 5, Vonage, etc.) implementa esta
interfaz. El Poller depende de la abstracción, no de un proveedor concreto.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CallResult:
    """Resultado de una llamada telefónica."""

    success: bool
    call_id: str | None = None
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class AlertPayload:
    """Datos que se pasan al notificador para construir el mensaje."""

    user_id: str
    phone: str
    event_name: str
    bout_id: str
    red_name: str | None = None
    blue_name: str | None = None
    weight_class: str | None = None
    minutes_until_start: int = 0


class VoiceNotifier(ABC):
    """Interfaz plug-in para proveedores de llamadas telefónicas."""

    @abstractmethod
    async def call(self, payload: AlertPayload) -> CallResult:
        """Realiza la llamada telefónica al usuario.

        Debe implementar reintentos internamente (D17: 3 intentos con backoff
        1 s / 5 s / 30 s) o delegar en el Poller.
        """
