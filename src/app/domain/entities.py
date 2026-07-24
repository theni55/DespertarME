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
    """Un combate dentro de una tarjeta de evento.

    Campos compartidos MMA y tenis (D47). En tenis:
    - `court` informa la pista; `Card.previous_bout()` busca el partido anterior
      en la misma pista por fecha en vez de matchNumber+1.
    - `round_description` contiene la ronda (QF, SF, Final...).
    - Sin `match_number` relevante (default 0), sin `card_segment`.
    - `sport` permite que `estimated_duration_seconds` y `elapsed_seconds`
      se calculen con valores especificos por deporte.
    """

    id: str
    match_number: int
    date: datetime
    card_segment: str | None = None
    weight_class: str | None = None
    periods: int = 3
    round_seconds: float = 300.0
    red: Athlete | None = None
    blue: Athlete | None = None
    court: str | None = None
    sport: str = "mma"
    round_description: str | None = None

    @property
    def estimated_duration_seconds(self) -> float:
        """Duracion media estimada del combate en segundos.

        MMA (D18): rounds * duracion_round + 1 min de descanso entre rounds.
        Tenis: periods * avg_set_seconds (best-of-3 ~90 min, best-of-5 ~150 min).
        """
        if self.sport == "tennis":
            avg_set_seconds = 2700.0
            return self.periods * avg_set_seconds
        rest_between = 60
        return self.periods * self.round_seconds + max(0, self.periods - 1) * rest_between


@dataclass(frozen=True)
class Card:
    """Tarjeta completa de un evento: lista de combates ordenados.

    Multi-sport (D47): si `sport == "tennis"` y los `Bout` tienen `court`,
    `previous_bout()` busca el partido anterior en la misma pista por fecha.
    """

    event_id: str
    event_name: str
    bouts: list[Bout] = field(default_factory=list)
    sport: str = "mma"

    def bout_by_match_number(self, match_number: int) -> Bout | None:
        return next((b for b in self.bouts if b.match_number == match_number), None)

    def bout_by_id(self, bout_id: str) -> Bout | None:
        return next((b for b in self.bouts if b.id == bout_id), None)

    def previous_bout(self, target: Bout) -> Bout | None:
        """Combate inmediatamente anterior al objetivo (D47).

        Tenis: partido anterior en la misma pista por fecha.
        MMA: matchNumber + 1 (comportamiento original, sin cambios).
        """
        if target.court is not None:
            same_court = [b for b in self.bouts if b.court == target.court and b.date < target.date]
            if not same_court:
                return None
            return max(same_court, key=lambda b: b.date)
        return self.bout_by_match_number(target.match_number + 1)


@dataclass(frozen=True)
class BoutStatus:
    """Estado en vivo de un combate en un instante dado.

    Multi-sport (D47): `sport` permite que `elapsed_seconds` se calcule con
    valores especificos. Tenis no tiene `clock` → se estima solo por sets
    completados.
    """

    bout_id: str
    state: BoutState
    clock: float = 0.0
    period: int = 0
    completed: bool = False
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    sport: str = "mma"

    @property
    def elapsed_seconds(self) -> float:
        """Tiempo transcurrido del combate si esta `in`, 0 si `pre`.

        MMA: `period * 300 - clock`. Tenis: `(period-1) * avg_set_seconds`
        (sin clock, estimacion conservadora por sets completados).
        """
        if self.state != "in":
            return 0.0
        if self.sport == "tennis":
            avg_set_seconds = 2700.0
            return max(0, self.period - 1) * avg_set_seconds
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
