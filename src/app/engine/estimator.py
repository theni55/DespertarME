"""EstimatorEngine (Fase 2a).

Lógica pura de recálculo del inicio estimado de un combate objetivo, en
función del estado en vivo del combate inmediatamente anterior.

Reglas (D15, D18):
- Combate previo en `pre` → el objetivo mantiene su fecha programada.
- Combate previo en `in` → `start_objetivo ≈ now + (duración_media − ya_transcurrido)
  + buffer_intercombate`.
- Combate previo en `post` → `start_objetivo = observed_at + buffer_intercombate` (D18: 5 min).
  `observed_at` es el instante en que el Poller observó por primera vez la
  transición `in→post` (persistido en Redis por `AlertState.remember_transition`,
  E2). Anclar a un momento fijo evita que la estimación se deslice hacia delante
  en cada poll (lo que hacía que `lead < 5 min` nunca disparase con D18=300s).

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
        observed_at: datetime | None = None,
    ) -> EstimatedStart:
        """Calcula el inicio estimado del combate objetivo.

        Args:
            card: tarjeta completa del evento.
            target: combate al que el usuario está suscrito.
            prev_status: estado en vivo del combate inmediatamente anterior
                (None si no hay combate anterior o aún no se ha consultado).
            now: instante actual (inyectable para tests).
            observed_at: instante en que se observó por primera vez la
                transición `in→post` del combate previo (E2). Opcional: si es
                None, en el branch `post` se usa `now` como fallback (comportamiento
                heredado, solo para tests unitarios sin Redis).
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
            # E2: anclar a la primera observación de la transición in→post, no a
            # `now`. Sin este anclaje, `start_at = now + buffer` se recalcula en
            # cada poll → delta constante = 300 s → `should_fire` nunca se cumple
            # con lead < 5 min, y con D40 la alarma local se reprograma al infinito.
            anchor = observed_at if observed_at is not None else now
            start_at = anchor + buffer
            anchor_note = "observed_at (E2)" if observed_at is not None else "now (sin ancla)"
            return EstimatedStart(
                bout_id=target.id,
                start_at=start_at,
                confidence="high",
                reason=(
                    f"previo terminado; {anchor_note} + buffer "
                    f"{int(buffer.total_seconds())}s (D18)"
                ),
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
