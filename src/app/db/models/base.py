"""Base declarativa común para todos los modelos de BD."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Constraint, DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Convención de nombres para constraints/keys/FKs/indexes. Permite que
# Alembic autogenere migraciones coherentes y que las migraciones a mano
# referencien nombres predecibles (necesario para la migración de Fase 7a
# que renombra FKs de user_id -> device_id).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Clase base declarativa (SQLAlchemy 2.x async)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# Re-export para typing en modelos que referencian Constraint directamente.
__all__ = ["Base", "Constraint", "utcnow"]
