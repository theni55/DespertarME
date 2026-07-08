"""Modelo de log de alertas (Fase 2b).

Audita cada alerta disparada. UNIQUE constraint `(subscription_id, bout_id,
fired_at_hour)` para idempotencia en BD (D16).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import Base


class AlertLog(Base):
    __tablename__ = "alert_log"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "bout_id", "fired_at_hour", name="uq_alert_idempotency"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subscription_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("bout_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bout_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    fired_at_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    notifier_response: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("fired", "failed", "skipped", name="alert_status"),
        default="fired",
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    subscription: Mapped[BoutSubscription] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="alerts"
    )
    user: Mapped[User] = relationship(back_populates="alerts")  # type: ignore[name-defined]  # noqa: F821
