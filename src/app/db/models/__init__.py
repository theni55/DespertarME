"""Exporta todos los modelos para que Alembic y SQLAlchemy los detecten."""

from app.db.models.alert_log import AlertLog
from app.db.models.base import Base
from app.db.models.subscriptions import (
    BoutSubscription,
    EventSubscription,
    SportSubscription,
)
from app.db.models.users import User

__all__ = [
    "AlertLog",
    "Base",
    "BoutSubscription",
    "EventSubscription",
    "SportSubscription",
    "User",
]
