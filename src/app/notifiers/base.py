"""Interfaz del notificador push (D7 original adaptado a FCM, D40).

FCM data-only high-priority se usa como "reprogramador" de la alarma local:
mensajes `update` (estimación movida), `started` (combate ya empezó),
`cancelled` (alerta cancelada) y `fire` (test-alarm: hacer sonar para prueba).
El sonido real lo reproduce la alarma local del dispositivo (Fase 7b).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

MessageType = Literal["update", "started", "cancelled", "fire"]


@dataclass(frozen=True)
class PushResult:
    """Resultado del envío push."""

    success: bool
    message_id: str | None = None
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass(frozen=True)
class AlertPayload:
    """Datos que se pasan al notifier para construir el mensaje FCM."""

    device_id: str
    fcm_token: str
    message_type: MessageType
    event_id: str
    bout_id: str
    event_name: str
    fighters: str | None = None
    estimated_start_at: str | None = None
    minutes_until_start: int | None = None
    weight_class: str | None = None

    def to_data(self) -> dict[str, str]:
        """Construye el dict data-only para FCM (todos los valores como str)."""
        data: dict[str, str] = {
            "type": self.message_type,
            "device_id": self.device_id,
            "event_id": self.event_id,
            "bout_id": self.bout_id,
            "event_name": self.event_name,
        }
        if self.fighters is not None:
            data["fighters"] = self.fighters
        if self.estimated_start_at is not None:
            data["estimated_start_at"] = self.estimated_start_at
        if self.minutes_until_start is not None:
            data["minutes_until_start"] = str(self.minutes_until_start)
        if self.weight_class is not None:
            data["weight_class"] = self.weight_class
        return data


class PushNotifier(ABC):
    """Interfaz plug-in para proveedores push (FCM, etc.)."""

    @abstractmethod
    async def send(self, payload: AlertPayload) -> PushResult:
        """Envía el mensaje push al device identificado en el payload."""
