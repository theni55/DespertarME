"""Interfaz comun para todos los providers de datos deportivos (D3).

Cada deporte/fuente (ESPN UFC, TheSportsDB, scraping tenis...) implementa esta
interfaz pluggable para que el EstimatorEngine y el Poller no dependan de una
fuente concreta.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.providers.models import CompetitionStatus, Event, EventSummary


class Provider(ABC):
    """Contrato que todo provider debe cumplir.

    Todos los metodos son async (async-first, convencion del proyecto).
    Las implementaciones deben aplicar backoff + circuit breaker (D20) en sus
    llamadas HTTP internas.
    """

    @abstractmethod
    async def list_upcoming_events(self) -> Sequence[EventSummary]:
        """Lista los eventos próximos (no pasados) de la liga/ deporte.

        Devuelve resumenes ligeros (id + nombre + fecha) suficientes para que
        el usuario seleccione a cuál suscribirse.
        """

    @abstractmethod
    async def get_event_card(self, event_id: str) -> Event:
        """Devuelve la tarjeta completa de un evento con todos sus combates.

        Los combates vienen ordenados por `matchNumber` (1 = main event).
        """

    @abstractmethod
    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        """Devuelve el estado en vivo de un combate concreto.

        Usado por el Poller para detectar transiciones `pre -> in -> post` del
        combate inmediatamente anterior al combate objetivo (D15).
        """
