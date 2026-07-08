"""Entidades de dominio (Fase 2a).

Entidades puras de negocio, independientes de la fuente de datos (provider)
y de la persistencia (BD). Se mapean desde los DTOs de `providers/models.py`
y las filas de BD en `db/models.py`.

Diseño: dataclasses inmutables (frozen=True) para razonamiento funcional y
seguridad en concurrencia. Sin lógica de I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

BoutState = Literal["pre", "in", "post"]


@dataclass(frozen=True)
class Athlete:
    id: str
    name: str | None = None


@dataclass(frozen=True)
class Bout:
    """Un combate dentro de una tarjeta de evento."""

    id: str
    match_number: int
    date: datetime
    card_segment: str | None = None
    weight_class: str | None = None
    periods: int = 3
    round_seconds: float = 300.0
    red: Athlete | None = None
    blue: Athlete | None = None

    @property
    def estimated_duration_seconds(self) -> float:
        """Duración media estimada del combate en segundos.

        Aproximación: rounds * duración_round + 1 min de descanso entre rounds.
        Para 3 rounds → 3*300 + 2*60 = 1020 s (~17 min).
        Para 5 rounds → 5*300 + 4*60 = 1740 s (~29 min).
        """
        rest_between = 60
        return self.periods * self.round_seconds + max(0, self.periods - 1) * rest_between


@dataclass(frozen=True)
class Card:
    """Tarjeta completa de un evento: lista de combates ordenados."""

    event_id: str
    event_name: str
    bouts: list[Bout] = field(default_factory=list)

    def bout_by_match_number(self, match_number: int) -> Bout | None:
        return next((b for b in self.bouts if b.match_number == match_number), None)

    def bout_by_id(self, bout_id: str) -> Bout | None:
        return next((b for b in self.bouts if b.id == bout_id), None)

    def previous_bout(self, target: Bout) -> Bout | None:
        """Combate inmediatamente anterior al objetivo en el orden de la tarjeta.

        El orden de la tarjeta es: matchNumber mayor = primero en pelear,
        matchNumber 1 = main event (último). El combate anterior al objetivo
        tiene matchNumber = target.match_number + 1.
        """
        return self.bout_by_match_number(target.match_number + 1)


@dataclass(frozen=True)
class BoutStatus:
    """Estado en vivo de un combate en un instante dado."""

    bout_id: str
    state: BoutState
    clock: float = 0.0
    period: int = 0
    completed: bool = False
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def elapsed_seconds(self) -> float:
        """Tiempo transcurrido del combate si está `in`, 0 si `pre`."""
        if self.state != "in":
            return 0.0
        return self.period * 300.0 - self.clock if self.clock >= 0 else 0.0


@dataclass(frozen=True)
class EstimatedStart:
    """Estimación del inicio real de un combate objetivo."""

    bout_id: str
    start_at: datetime
    confidence: Literal["high", "medium", "low"] = "medium"
    reason: str = ""

    def should_fire(self, now: datetime, lead_seconds: int) -> bool:
        """¿Debe dispararse la alerta ahora? `start_at - now <= lead_seconds`."""
        delta = (self.start_at - now).total_seconds()
        return delta <= lead_seconds


@dataclass(frozen=True)
class Subscription:
    """Suscripción de un usuario a un combate concreto."""

    id: str
    user_id: str
    bout_id: str
    event_id: str
    lead_minutes: int = 15
    target_match_number: int = 1
    previous_match_number: int | None = None
