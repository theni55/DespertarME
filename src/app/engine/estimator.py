"""EstimatorEngine (Fase 2a).

Lógica pura de recálculo del inicio estimado de un combate objetivo, en
función del estado en vivo del combate inmediatamente anterior.

Reglas (D15, D18):
- Combate previo en `pre` → el objetivo mantiene su fecha programada.
- Combate previo en `in` → `start_objetivo ≈ now + (duración_media − ya_transcurrido)
  + buffer_intercombate`.
- Combate previo en `post` → `start_objetivo = now + buffer_intercombate` (D18: 5 min).

Cadencia de polling (D15): el motor indica qué intervalo usar al Poller según
el estado del combate previo.

Sin I/O: recibe dataclasses del dominio y devuelve dataclasses. Tests con
freezegun + provider fake (sin Redis, sin BD).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.entities import (
    Bout,
    BoutState,
    BoutStatus,
    Card,
    EstimatedStart,
)


@dataclass(frozen=True)
class EstimatorConfig:
    """Configuración del estimador (valores por defecto D18)."""

    buffer_intercombate_seconds: int = 300
    default_lead_minutes: int = 15
    poll_default_seconds: int = 60
    poll_prev_in_advanced_seconds: int = 10
    poll_prev_post_seconds: int = 5


class EstimatorEngine:
    """Motor puro de estimación del inicio real de un combate.

    Sin estado mutable: cada llamada es pura y depende solo de sus argumentos.
    """

    def __init__(self, config: EstimatorConfig | None = None) -> None:
        self.config = config or EstimatorConfig()

    def estimate(
        self,
        card: Card,
        target: Bout,
        prev_status: BoutStatus | None,
        now: datetime,
    ) -> EstimatedStart:
        """Calcula el inicio estimado del combate objetivo.

        Args:
            card: tarjeta completa del evento.
            target: combate al que el usuario está suscrito.
            prev_status: estado en vivo del combate inmediatamente anterior
                (None si no hay combate anterior o aún no se ha consultado).
            now: instante actual (inyectable para tests).
        """
        prev = card.previous_bout(target)
        if prev is None:
            return EstimatedStart(
                bout_id=target.id,
                start_at=target.date,
                confidence="medium",
                reason="no hay combate previo; fecha programada",
            )

        if prev_status is None:
            return EstimatedStart(
                bout_id=target.id,
                start_at=target.date,
                confidence="low",
                reason="sin datos del combate previo; uso fecha programada",
            )

        buffer = timedelta(seconds=self.config.buffer_intercombate_seconds)

        if prev_status.state == "pre":
            return EstimatedStart(
                bout_id=target.id,
                start_at=target.date,
                confidence="low",
                reason="combate previo aún no empezado; fecha programada",
            )

        if prev_status.state == "in":
            remaining = prev.estimated_duration_seconds - prev_status.elapsed_seconds
            if remaining < 0:
                remaining = 0
            start_at = now + timedelta(seconds=remaining) + buffer
            return EstimatedStart(
                bout_id=target.id,
                start_at=start_at,
                confidence="medium",
                reason=(
                    f"previo en curso (round {prev_status.period}, "
                    f"restan ~{int(remaining)}s + buffer {int(buffer.total_seconds())}s)"
                ),
            )

        if prev_status.state == "post":
            start_at = now + buffer
            return EstimatedStart(
                bout_id=target.id,
                start_at=start_at,
                confidence="high",
                reason=f"previo terminado; ahora + buffer {int(buffer.total_seconds())}s (D18)",
            )

        return EstimatedStart(
            bout_id=target.id,
            start_at=target.date,
            confidence="low",
            reason="estado desconocido; fecha programada",
        )

    def poll_interval(self, prev_state: BoutState | None) -> int:
        """Cadencia de polling adaptativa según el estado del combate previo (D15).

        - None / pre → 60 s (reposo)
        - in → 10 s (equilibrio precisión/coste)
        - post → 5 s (máxima precisión, buffer pequeño)
        """
        if prev_state is None or prev_state == "pre":
            return self.config.poll_default_seconds
        if prev_state == "in":
            return self.config.poll_prev_in_advanced_seconds
        if prev_state == "post":
            return self.config.poll_prev_post_seconds
        return self.config.poll_default_seconds
