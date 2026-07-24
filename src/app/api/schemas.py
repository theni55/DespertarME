"""Esquemas Pydantic para la API REST (Fase 7a: device model, sin User/Twilio).

DTOs para:
- Devices: registro/upsert de FCM token vía `POST /api/devices`.
- Subscriptions: alertas de combates (sin `previous_bout_id` que ahora deriva
  el backend E4; `lead_minutes` validado >=5 mientras no se arregle E2).
- Alert log: historial auditable de pushes enviados.
- Events: lista + tarjeta (con `previous_bout_id` calculado server-side) para
  las pantallas Home/Eventos/EventDetail de la app.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# E2 sigue sin arreglarse del todo en producción (necesita datos reales para
# calibrar el buffer); para evitar estimaciones "post" inalcanzables con
# D18=300s, exigimos un lead mínimo de 5 minutos.
MIN_LEAD_MINUTES = 5


class DeviceCreate(BaseModel):
    """Registro/upsert de device. `device_id` lo genera el cliente (UUID v4
    en `expo-secure-store`); el backend solo valida/registra el FCM token."""

    device_id: str = Field(min_length=32, max_length=36)
    fcm_token: str = Field(min_length=10, max_length=512)
    platform: str | None = Field(default=None, max_length=10)
    timezone: str = "Europe/Madrid"
    locale: str | None = Field(default=None, max_length=10)

    @field_validator("device_id")
    @classmethod
    def _validate_device_id(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("device_id no puede estar vacío")
        return v


class DeviceOut(BaseModel):
    id: str
    fcm_token: str | None = None
    platform: str | None = None
    timezone: str
    locale: str | None = None
    is_active: bool
    last_seen_at: datetime

    model_config = {"from_attributes": True}


class BoutSubscriptionCreate(BaseModel):
    """Crear alerta. El cliente NO manda `previous_bout_id`: el backend lo
    deriva en runtime desde la card fresca en cada poll (E4), porque UFC
    reordena la card el dia del evento.

    Multi-sport (D47): `sport` indica el deporte ("mma"|"tennis") — default "mma"
    para backward-compatibilidad."""

    event_id: str
    bout_id: str
    target_match_number: int = 0
    lead_minutes: int = 15
    sport: str = "mma"

    @field_validator("lead_minutes")
    @classmethod
    def _validate_lead(cls, v: int) -> int:
        if v < MIN_LEAD_MINUTES:
            raise ValueError(f"lead_minutes debe ser >= {MIN_LEAD_MINUTES}")
        return v


class BoutSubscriptionOut(BaseModel):
    id: str
    device_id: str
    event_id: str
    bout_id: str
    target_match_number: int
    lead_minutes: int
    status: str
    sport: str = "mma"

    model_config = {"from_attributes": True}


class AlertLogOut(BaseModel):
    id: str
    subscription_id: str
    device_id: str
    bout_id: str
    fired_at: datetime
    fired_at_epoch_hour: int
    status: str
    attempts: int
    notifier_response: str | None = None
    payload: str | None = None

    model_config = {"from_attributes": True}


class BoutAthleteOut(BaseModel):
    id: str
    name: str | None = None
    headshot_url: str | None = None


class BoutOut(BaseModel):
    """Combate en la tarjeta de un evento.

    Multi-sport (D47): `court`, `sport` y `round_description` son campos
    especificos de tenis (None para MMA)."""

    id: str
    match_number: int
    date: datetime
    card_segment: str | None = None
    weight_class: str | None = None
    periods: int = 3
    red: BoutAthleteOut | None = None
    blue: BoutAthleteOut | None = None
    previous_bout_id: str | None = None  # E4: calculado server-side
    court: str | None = None
    sport: str = "mma"
    round_description: str | None = None


class EventSummaryOut(BaseModel):
    """Resumen ligero para la lista de eventos (pantalla Eventos de la app)."""

    id: str
    name: str
    date: datetime
    # D42: ESPN no sirve `images` en EventSummary hoy; la app usa `hero.webp`
    # estática como fallback. El backend deja el campo para la mejora futura.
    image_url: str | None = None


class EventCardOut(BaseModel):
    """Tarjeta completa de un evento con bouts ordenados (pantalla EventDetail)."""

    id: str
    name: str
    date: datetime
    image_url: str | None = None
    bouts: list[BoutOut]
