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

from app.config import settings

# E2 sigue sin arreglarse del todo en producción (necesita datos reales para
# calibrar el buffer); para evitar estimaciones "post" inalcanzables con
# D18=300s, exigimos un lead mínimo de 5 minutos para MMA/Tenis.
# D56 NBA: Q2-Q4 permiten lead=0 ("Cuando empieza") — la alarma dispara a
# `est - 60s` con cushion de 1 min sobre lead 0 (mismo patrón D45).
MIN_LEAD_MINUTES = 5
NBA_QUARTER_LEAD_MINUTES = 0

# A11: allowlist de deportes/ligas soportados por el poller. Evita suscripciones
# a deportes/ligas inexistentes que el poller no podria procesar (warnings por
# sub cada minuto).
ALLOWED_SPORTS = {"mma", "tennis", "nba", "nfl", "football"}
TENNIS_LEAGUES = {"atp", "wta"}


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

    Multi-sport (D47): `sport` indica el deporte ("mma"|"tennis"|"nba") —
    default "mma" para backward-compatibilidad.

    D56 NBA: lead=0 permitido para Q2-Q4 ("Cuando empieza"); Q1 sigue
    requiriendo >=5 min (es el inicio del partido, mismo modelo que MMA/Tenis)."""

    event_id: str
    bout_id: str
    target_match_number: int = 0
    lead_minutes: int = 15
    sport: str = "mma"
    league: str = ""

    @field_validator("lead_minutes")
    @classmethod
    def _validate_lead(cls, v: int) -> int:
        # D56 NBA Q2-Q4: lead=0 ("Cuando empieza"). El resto (MMA/Tenis/NBA Q1)
        # requiere >= MIN_LEAD_MINUTES (5). La validacion de "Q2-Q4 NBA" no se
        # puede hacer aqui sin saber el `target_match_number`; la UI restringe
        # en cliente. Aqui solo validamos el rango absoluto >= 0.
        if v < 0:
            raise ValueError("lead_minutes debe ser >= 0")
        return v

    def validate_for_sport(self) -> None:
        """Validacion contextual post-load: la UI debe llamar esta antes de
        persistir. Permite lead=0 solo para NBA/NFL Q2-Q4. A11: valida que el
        deporte y la liga existan en el registry del poller.
        """
        if self.sport not in ALLOWED_SPORTS:
            raise ValueError(f"Deporte no soportado: {self.sport}")
        if self.sport == "tennis" and self.league not in TENNIS_LEAGUES:
            raise ValueError(
                f"Liga de tenis invalida: {self.league!r} (se espera 'atp' o 'wta')"
            )
        if self.sport == "football" and self.league not in set(settings.football_leagues):
            raise ValueError(f"Liga de futbol invalida: {self.league!r}")

        if self.sport in ("nba", "nfl") and self.target_match_number in (2, 3, 4):
            if self.lead_minutes != NBA_QUARTER_LEAD_MINUTES:
                raise ValueError(f"NBA Q2-Q4 requiere lead_minutes={NBA_QUARTER_LEAD_MINUTES}")
        else:
            if self.lead_minutes < MIN_LEAD_MINUTES:
                raise ValueError(f"lead_minutes debe ser >= {MIN_LEAD_MINUTES}")


class BoutSubscriptionOut(BaseModel):
    id: str
    device_id: str
    event_id: str
    bout_id: str
    target_match_number: int
    lead_minutes: int
    status: str
    sport: str = "mma"
    league: str = ""

    model_config = {"from_attributes": True}


class AlertLogOut(BaseModel):
    id: str
    subscription_id: str
    device_id: str
    bout_id: str
    message_type: str | None = None
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
    status: str | None = None  # "pre" | "in" | "post" | None


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
