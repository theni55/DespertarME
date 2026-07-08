"""Modelo de usuarios (Fase 3: auth JWT + multiusuario)."""

from __future__ import annotations

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.alert_log import AlertLog
from app.db.models.base import Base
from app.db.models.subscriptions import BoutSubscription, EventSubscription, SportSubscription


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_normalized: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Madrid", nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("user", "admin", name="user_role"), default="user", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sport_subscriptions: Mapped[list[SportSubscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    event_subscriptions: Mapped[list[EventSubscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    bout_subscriptions: Mapped[list[BoutSubscription]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    alerts: Mapped[list[AlertLog]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
