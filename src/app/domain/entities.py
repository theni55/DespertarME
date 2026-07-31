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
        NBA (D56): un cuarto sintetico = `periods * round_seconds`. El buffer
            inter-cuarto (halftime vs comercial corto) lo anade el estimator
            aparte (D57 callback `buffer_for`), no entra aqui.
        """
        if self.sport == "tennis":
            avg_set_seconds = 2700.0
            return self.periods * avg_set_seconds
        if self.sport == "nba":
            # Bout = un cuarto. `periods` sintetico es siempre 1; `round_seconds`
            # es 720 (12:00 reglamentario). El descanso inter-cuarto se anade
            # aparte en el estimator (D57 `buffer_for`), no en la duracion.
            return self.periods * self.round_seconds
        if self.sport == "football":
            # Bout = un partido completo (2 tiempos de 45 min).
            return 2 * 2700.0
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
        """Combate inmediatamente anterior al objetivo (D47, D56).

        Tenis: partido anterior en la misma pista por fecha.
        NBA (D56): matchNumber ASCIENDE con el tiempo (Q1=mn1, Q4=mn4) ->
            previo es mn-1.
        MMA: matchNumber DESCIENDE con el tiempo (mn1=main event=ultimo de
            la card) -> previo es mn+1 (comportamiento original).
        """
        if target.court is not None:
            same_court = [b for b in self.bouts if b.court == target.court and b.date < target.date]
            if not same_court:
                return None
            return max(same_court, key=lambda b: b.date)
        # NBA: prev temporal es mn-1 (mn asciende con el tiempo).
        # Football (MVP): 1 bout/partido -> sin previo.
        # MMA: mn+1 (mn desciende con el tiempo).
        if self.sport == "nba":
            return self.bout_by_match_number(target.match_number - 1)
        if self.sport == "football":
            return None
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

        MMA: `period * 300 - clock` (clock = segundos transcurridos del round).
        Tenis: `(period-1) * avg_set_seconds` (sin clock, estimacion conservadora
            por sets completados).
        NBA (D56): `Bout` = un cuarto. `period` = numero del cuarto en el
            juego global (1..4 o mas para OT). `clock` = segundos restantes
            (count-down desde 720.0). Elapsed = `(period-1)*720 + (720 - clock)`
            — suma lo jugado en cuartos anteriores mas lo jugado en el actual.
        """
        if self.state != "in":
            return 0.0
        if self.sport == "tennis":
            avg_set_seconds = 2700.0
            return max(0, self.period - 1) * avg_set_seconds
        if self.sport == "nba":
            # Period 1-indexed; clock = segundos restantes del cuarto actual.
            # Si el tout es la Q2 (period=2) y clock=300, elapsed = 720 + 420.
            return max(0.0, (self.period - 1) * 720.0 + (720.0 - self.clock))
        if self.sport == "football":
            # Period 1-indexed (1=1st half, 2=2nd half); clock = segundos
            # transcurridos del tiempo actual (count-up desde 0 del half).
            return max(0.0, (self.period - 1) * 2700.0 + self.clock)
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
