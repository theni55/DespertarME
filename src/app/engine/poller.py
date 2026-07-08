"""Poller de alertas (Fase 2b).

Orquesta el flujo de una alerta:
1. Carga suscripciones activas de la BD.
2. Consulta el estado del combate previo vía Provider.
3. EstimatorEngine recalcula el inicio del combate objetivo.
4. Si `start - now <= lead_minutes` → idempotencia (Redis) → notifier.call.
5. Si la llamada falla → reintentos con backoff (D17: 1 s / 5 s / 30 s).
6. Registra en `alert_log` (BD, auditable) con UNIQUE constraint de idempotencia.

El Poller está diseñado para ejecutarse periódicamente (APScheduler). Cada
ejecución procesa todas las suscripciones activas; la cadencia entre
ejecuciones la decide el scheduler según el estado del combate previo (D15).
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.alert_log import AlertLog
from app.db.models.subscriptions import BoutSubscription
from app.domain.entities import (
    Athlete,
    Bout,
    BoutStatus,
    Card,
    EstimatedStart,
)
from app.engine.estimator import EstimatorEngine
from app.engine.state import AlertState
from app.notifiers.base import AlertPayload, CallResult, VoiceNotifier
from app.providers.base import Provider

logger = logging.getLogger(__name__)

# Backoff de reintentos de llamada (D17): 1 s / 5 s / 30 s.
RETRY_DELAYS = (1.0, 5.0, 30.0)


class Poller:
    """Procesa suscripciones activas y dispara alertas cuando corresponde."""

    def __init__(
        self,
        *,
        provider: Provider,
        notifier: VoiceNotifier,
        state: AlertState,
        estimator: EstimatorEngine | None = None,
        retry_delays: tuple[float, ...] = RETRY_DELAYS,
    ) -> None:
        self._provider = provider
        self._notifier = notifier
        self._state = state
        self._estimator = estimator or EstimatorEngine()
        self._retry_delays = retry_delays

    async def poll_once(self, session: AsyncSession, now: datetime | None = None) -> int:
        """Procesa todas las suscripciones activas. Devuelve nº de alertas disparadas."""
        now = now or datetime.now(UTC)
        fired_count = 0

        result = await session.execute(
            sa.select(BoutSubscription).where(BoutSubscription.status == "active")
        )
        subs = result.scalars().all()

        for sub in subs:
            try:
                if await self._process_subscription(session, sub, now):
                    fired_count += 1
            except Exception:
                logger.exception("Error procesando suscripción %s", sub.id)

        return fired_count

    async def _process_subscription(
        self, session: AsyncSession, sub: BoutSubscription, now: datetime
    ) -> bool:
        """Procesa una suscripción. Devuelve True si se disparó la alerta."""
        card = await self._load_card(sub)
        target = card.bout_by_id(sub.bout_id)
        if target is None:
            logger.warning(
                "Combate %s no encontrado en la tarjeta del evento %s", sub.bout_id, sub.event_id
            )
            return False

        prev_bout_status: BoutStatus | None = None
        if sub.previous_bout_id:
            raw = await self._provider.get_competition_status(sub.event_id, sub.previous_bout_id)
            prev_bout_status = BoutStatus(
                bout_id=sub.previous_bout_id,
                state=raw.type.state,
                clock=raw.clock,
                period=raw.period,
                completed=raw.type.completed,
            )

        estimate = self._estimator.estimate(card, target, prev_bout_status, now)
        lead_seconds = sub.lead_minutes * 60

        if not estimate.should_fire(now, lead_seconds):
            logger.debug(
                "Suscripción %s: aún no toca (start=%s, now=%s, lead=%dm)",
                sub.id,
                estimate.start_at,
                now,
                sub.lead_minutes,
            )
            return False

        status_key = prev_bout_status.state if prev_bout_status else "pre"
        if not await self._state.try_mark_fired(sub.id, sub.bout_id, status_key):
            logger.info("Suscripción %s: alerta ya disparada (idempotente)", sub.id)
            return False

        result = await self._call_with_retries(sub, target, estimate, now)
        await self._log_alert(session, sub, target, estimate, result, now, status_key)

        if result.success:
            sub.status = "fired"
            await session.commit()
            logger.info("Alerta disparada para suscripción %s", sub.id)
            return True

        logger.warning("Alerta fallida para suscripción %s tras reintentos", sub.id)
        return False

    async def _load_card(self, sub: BoutSubscription) -> Card:
        """Carga la tarjeta del evento vía Provider y mapea a dominio."""
        event = await self._provider.get_event_card(sub.event_id)
        bouts: list[Bout] = []
        for comp in event.bouts:
            red = comp.red_corner
            blue = comp.blue_corner
            bouts.append(
                Bout(
                    id=comp.id,
                    match_number=comp.match_number,
                    date=datetime.fromisoformat(comp.date.replace("Z", "+00:00")),
                    card_segment=comp.card_segment.name if comp.card_segment else None,
                    weight_class=comp.weight_class.text if comp.weight_class else None,
                    periods=comp.format.regulation.periods if comp.format else 3,
                    round_seconds=comp.format.regulation.clock if comp.format else 300.0,
                    red=Athlete(id=red.id) if red else None,
                    blue=Athlete(id=blue.id) if blue else None,
                )
            )
        return Card(event_id=event.id, event_name=event.name, bouts=bouts)

    async def _call_with_retries(
        self,
        sub: BoutSubscription,
        target: Bout,
        estimate: EstimatedStart,
        now: datetime,
    ) -> CallResult:
        """Llama al notifier con reintentos (D17: 1 s / 5 s / 30 s)."""
        minutes_until = max(0, int((estimate.start_at - now).total_seconds() // 60))
        payload = AlertPayload(
            user_id=sub.user_id,
            phone="+000000000",
            event_name="",
            bout_id=sub.bout_id,
            red_name=None,
            blue_name=None,
            weight_class=target.weight_class,
            minutes_until_start=minutes_until,
        )
        last_result: CallResult = CallResult(success=False, error="no attempts")
        for attempt, delay in enumerate((0.0, *self._retry_delays)):
            if delay > 0:
                await asyncio.sleep(delay)
            logger.debug("Intento %d de llamada para suscripción %s", attempt + 1, sub.id)
            last_result = await self._notifier.call(payload)
            if last_result.success:
                return last_result
        return last_result

    async def _log_alert(
        self,
        session: AsyncSession,
        sub: BoutSubscription,
        target: Bout,
        estimate: EstimatedStart,
        result: CallResult,
        now: datetime,
        status_key: str,
    ) -> None:
        """Registra la alerta en BD (alert_log) con idempotencia UNIQUE."""
        payload = json.dumps(
            {
                "bout_id": sub.bout_id,
                "estimate_start": estimate.start_at.isoformat(),
                "confidence": estimate.confidence,
                "reason": estimate.reason,
                "weight_class": target.weight_class,
            },
            ensure_ascii=False,
        )
        log = AlertLog(
            id=str(uuid.uuid4()),
            subscription_id=sub.id,
            user_id=sub.user_id,
            bout_id=sub.bout_id,
            fired_at=now,
            fired_at_hour=now.hour,
            payload=payload,
            notifier_response=result.call_id or result.error,
            status="fired" if result.success else "failed",
            attempts=len(self._retry_delays) + 1,
        )
        try:
            session.add(log)
            await session.commit()
        except sa.exc.IntegrityError:
            logger.info("alert_log: duplicado evitado por UNIQUE constraint (D16)")
            await session.rollback()
