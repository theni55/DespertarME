"""Modelo de suscripción a un combate (Fase 2b + Fase 7a).

`BoutSubscription` es la suscripción que dispara el Poller: un Device quiere
ser avisado X minutos antes de un combate concreto de un evento. El campo
`previous_bout_id` NO se persiste (E4): se deriva en runtime desde la card
fresca del evento en cada poll, porque UFC reordena la card el día del evento.

UNIQUE `(device_id, bout_id)` (E6) impide que un tap de re-suscripción genere
push duplicados para el mismo combate.
"""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class BoutSubscription(Base):
    """Suscripcion de alerta a un combate concreto (la que dispara el Poller).

    Multi-sport (D47): `sport` indica el deporte ("mma"|"tennis") para que el
    Poller use el Provider correcto al procesar la suscripcion.
    """

    __tablename__ = "bout_subscriptions"
    __table_args__ = (
        UniqueConstraint("device_id", "bout_id", name="uq_bout_subscriptions_device_bout"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    device_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    bout_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_match_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    sport: Mapped[str] = mapped_column(String(20), default="mma", nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "fired", "cancelled", name="subscription_status"),
        default="active",
        nullable=False,
        index=True,
    )

    alerts: Mapped[list[AlertLog]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="subscription", cascade="all, delete-orphan"
    )
