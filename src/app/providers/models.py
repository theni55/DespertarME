"""DTOs de parsing de ESPN Core API (D9, D13).

Modelos pydantic con `extra="ignore"` porque ESPN devuelve muchos campos que no
necesitamos; solo modelamos lo que el EstimatorEngine/Poller consumen.

Estos DTOs viven en la capa provider (parsing). En Fase 2a se crearan las
entidades de dominio (`domain/entities.py`) con la logica de negocio, mapeando
desde estos DTOs.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Estado del combate segun ESPN status.type.state (verificado en vivo).
BoutState = Literal["pre", "in", "post"]

_ATHLETE_ID_RE = re.compile(r"/athletes/(\d+)")


class _ESPNBase(BaseModel):
    model_config = ConfigDict(extra="ignore")


class AthleteRef(_ESPNBase):
    """Referencia (URL) a un atleta; el nombre se resuelve bajo demanda."""

    ref: str = Field(alias="$ref")

    @property
    def athlete_id(self) -> str | None:
        """Extrae el id del atleta del `$ref` (ej. `.../athletes/4686725?lang=en`)."""
        m = _ATHLETE_ID_RE.search(self.ref)
        return m.group(1) if m else None


class AthleteHeadshot(_ESPNBase):
    href: str
    alt: str | None = None


class AthleteDetail(_ESPNBase):
    """Detalle de un atleta (`/sports/mma/athletes/{id}`): nombre + foto."""

    id: str
    display_name: str = Field(default="", alias="displayName")
    nickname: str | None = None
    headshot: AthleteHeadshot | None = None

    @property
    def headshot_url(self) -> str | None:
        """URL de la foto de la cara; fallback al patrón CDN estándar de ESPN."""
        if self.headshot and self.headshot.href:
            return self.headshot.href
        if self.id:
            return f"https://a.espncdn.com/i/headshots/mma/players/full/{self.id}.png"
        return None


class Competitor(_ESPNBase):
    """Un lado de un combate (red corner=order 1, blue=order 2).

    En tenis, el nombre viene inline (D49): el campo `name` se rellena
    directamente desde el JSON de ESPN sin necesidad de seguir el `$ref`."""

    id: str
    order: int
    winner: bool = False
    athlete: AthleteRef | None = None
    name: str | None = None


class CardSegment(_ESPNBase):
    name: str
    description: str | None = None


class BoutRegulation(_ESPNBase):
    periods: int
    clock: float = 0.0


class BoutFormat(_ESPNBase):
    regulation: BoutRegulation


class WeightClass(_ESPNBase):
    """Categoria de peso del combate (ESPN `competition.type`).

    En tenis, `type.text` contiene el tipo de partido (e.g. "Men's Singles").
    `extra="ignore"` descarta campos extra como `slug`/`type` de tenis."""

    text: str | None = None
    abbreviation: str | None = None


class TennisCourt(_ESPNBase):
    """Pista de un partido de tenis (D46)."""

    description: str


class TennisRound(_ESPNBase):
    """Ronda de un partido de tenis (D46)."""

    round_type: int = Field(alias="roundType")
    description: str | None = None
    abbreviation: str | None = None


class Bout(_ESPNBase):
    """Un combate individual dentro de una tarjeta (competition en ESPN).

    Campos compartidos MMA y tenis (D46/D47). En tenis:
    - No hay `matchNumber` → default 0 (orden por `date` dentro de cada `court`).
    - `court` informa la pista (Center Court, etc.).
    - `round` informa la ronda (QF, SF, Final...).
    - Los nombres de jugadores vienen inline en `competitors[].name` (D49).
    """

    id: str
    match_number: int = Field(default=0, alias="matchNumber")
    date: str
    end_date: str | None = Field(default=None, alias="endDate")
    weight_class: WeightClass | None = Field(default=None, alias="type")
    card_segment: CardSegment | None = Field(default=None, alias="cardSegment")
    format: BoutFormat | None = None
    competitors: list[Competitor] = Field(default_factory=list)
    court: TennisCourt | None = None
    round: TennisRound | None = None

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
