"""DTOs de parsing de ESPN Core API (D9, D13).

Modelos pydantic con `extra="ignore"` porque ESPN devuelve muchos campos que no
necesitamos; solo modelamos lo que el EstimatorEngine/Poller consumen.

Estos DTOs viven en la capa provider (parsing). En Fase 2a se crearan las
entidades de dominio (`domain/entities.py`) con la logica de negocio, mapeando
desde estos DTOs.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Estado del combate segun ESPN status.type.state (verificado en vivo).
BoutState = Literal["pre", "in", "post"]


class _ESPNBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


class AthleteRef(_ESPNBase):
    """Referencia (URL) a un atleta; el nombre se resuelve bajo demanda."""

    ref: str = Field(alias="$ref")


class Competitor(_ESPNBase):
    """Un lado de un combate (red corner=order 1, blue=order 2)."""

    id: str
    order: int
    winner: bool = False
    athlete: AthleteRef | None = None


class CardSegment(_ESPNBase):
    name: str
    description: str | None = None


class BoutRegulation(_ESPNBase):
    periods: int
    clock: float


class BoutFormat(_ESPNBase):
    regulation: BoutRegulation


class WeightClass(_ESPNBase):
    """Categoria de peso del combate (ESPN `competition.type`)."""

    text: str | None = None
    abbreviation: str | None = None


class Bout(_ESPNBase):
    """Un combate individual dentro de una tarjeta (competition en ESPN)."""

    id: str
    match_number: int = Field(alias="matchNumber")
    date: str
    end_date: str | None = Field(default=None, alias="endDate")
    weight_class: WeightClass | None = Field(default=None, alias="type")
    card_segment: CardSegment | None = Field(default=None, alias="cardSegment")
    format: BoutFormat | None = None
    competitors: list[Competitor] = Field(default_factory=list)

    @property
    def red_corner(self) -> Competitor | None:
        return next((c for c in self.competitors if c.order == 1), None)

    @property
    def blue_corner(self) -> Competitor | None:
        return next((c for c in self.competitors if c.order == 2), None)


class CompetitionStatusType(_ESPNBase):
    state: BoutState
    completed: bool = False
    description: str | None = None
    short_detail: str | None = Field(default=None, alias="shortDetail")


class CompetitionStatus(_ESPNBase):
    """Salida de `/events/{id}/competitions/{cId}/status` (D13)."""

    clock: float = 0.0
    display_clock: str | None = Field(default=None, alias="displayClock")
    period: int = 0
    type: CompetitionStatusType


class EventSummary(_ESPNBase):
    """Resumen ligero de un evento (id + nombre + fecha)."""

    id: str
    name: str
    date: str


class Event(_ESPNBase):
    """Tarjeta completa de un evento con todos sus combates."""

    id: str
    name: str
    date: str
    bouts: list[Bout] = Field(default_factory=list, alias="competitions")
