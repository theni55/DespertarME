"""Interfaz comun para todos los providers de datos deportivos (D3).

Cada deporte/fuente (ESPN UFC, TheSportsDB, scraping tenis...) implementa esta
interfaz pluggable para que el EstimatorEngine y el Poller no dependan de una
fuente concreta.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import datetime

from app.providers.models import AthleteDetail, CompetitionStatus, Event, EventSummary


class Provider(ABC):
    """Contrato que todo provider debe cumplir.

    Todos los metodos son async (async-first, convencion del proyecto).
    Las implementaciones deben aplicar backoff + circuit breaker (D20) en sus
    llamadas HTTP internas.
    """

    @abstractmethod
    async def list_upcoming_events(
        self, *, min_date: datetime | None = None, max_concurrent: int = 4
    ) -> Sequence[EventSummary]:
        """Lista los eventos proximos (no pasados) de la liga/deporte.

        `min_date`: opcional, filtra eventos cuya fecha sea anterior a esta
        (default: ahora UTC). `max_concurrent`: limite de fetches paralelos.
        """

    @abstractmethod
    async def get_event_card(self, event_id: str) -> Event:
        """Devuelve la tarjeta completa de un evento con todos sus combates."""

    @abstractmethod
    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        """Devuelve el estado en vivo de un combate concreto."""

    @abstractmethod
    async def get_athlete(self, athlete_id: str) -> AthleteDetail:
        """Devuelve el detalle de un atleta (nombre + foto)."""

    async def aclose(self) -> None:  # noqa: B027
        """Cierra recursos (httpx client, etc.). Implementacion por defecto nop."""
