"""Modelos de suscripciones (Fase 2b + 3).

- SportSubscription: usuario sigue un deporte (MMA, Boxeo...).
- EventSubscription: usuario sigue un evento concreto.
- BoutSubscription: usuario quiere ser avisado X min antes de un combate;
  es la suscripción que dispara el Poller.
"""

from __future__ import annotations

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class SportSubscription(Base):
    __tablename__ = "sport_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    user: Mapped[User] = relationship(back_populates="sport_subscriptions")  # type: ignore[name-defined]  # noqa: F821


class EventSubscription(Base):
    __tablename__ = "event_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(back_populates="event_subscriptions")  # type: ignore[name-defined]  # noqa: F821


class BoutSubscription(Base):
    """Suscripción de alerta a un combate concreto (la que dispara el Poller)."""

    __tablename__ = "bout_subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    bout_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_match_number: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_bout_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_match_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lead_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("active", "fired", "cancelled", name="subscription_status"),
        default="active",
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship(back_populates="bout_subscriptions")  # type: ignore[name-defined]  # noqa: F821
    alerts: Mapped[list[AlertLog]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="subscription", cascade="all, delete-orphan"
    )
