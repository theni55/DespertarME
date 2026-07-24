"""Poller de alertas (Fase 2b + Fase 7a).

Orquesta el flujo por cada suscripción activa:

1. Carga suscripciones activas agrupadas por `event_id` (E8: 1 fetch ESPN por
   evento y ciclo, no N).
2. Para cada suscripción:
   a. Carga el `Device`; skip si no existe, inactivo o sin `fcm_token`.
   b. Deriva `previous_bout_id` desde la card fresca (E4: no congela el valor
      que mandó el cliente; las reordenaciones de UFC día-de-evento ya no
      producen estimaciones incoherentes).
   c. **E3** — Guard del estado del combate objetivo: si el target ya está
      `in` → push `started`; si `post` → push `cancelled`. No se estima un
      "empieza en 5 min" horas después del combate.
   d. Calcula estimación. Si el previo está `post` (E2), ancla el `start_at`
      al `observed_at` persistido en Redis (no se desliza al infinito).
   e. **D40 push on-change**: si la estimación se movió > `MIN_DELTA_SECONDS`
      desde el último push → envía `update` con `estimated_start_at`.
   f. Marca idempotencia (Redis + UNIQUE BD) tras éxito (E6) y registra en
      `alert_log` con `fired_at_epoch_hour` (E6).
3. Reintentos recortados a 1 corto (E7: 36 s de sleep acumulado no tiene sentido
   para FCM idempotente y barato).

El sonido no lo dispara el Poller (D40): la app programa una alarma local
(`AlarmManager.setAlarmClock`) a `estimated_start_at − lead` con cada `update`
recibido. El Poller solo mantiene la estimación fresca en el dispositivo.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from datetime import UTC, datetime

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.alert_log import AlertLog
from app.db.models.devices import Device
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
from app.notifiers.base import AlertPayload, PushNotifier, PushResult
from app.providers.athletes import AthleteResolver
from app.providers.base import Provider
from app.providers.models import Competitor as ProviderCompetitor

logger = logging.getLogger(__name__)

# E7: recortamos los 3 sleep de 1/5/30 s (36 s acumulados) a un único retry
# corto de 2 s. FCM es idempotente, barato y sin estado de sesión: no tiene
# sentido bloquear el ciclo del poll 36 s por sub fallida.
RETRY_DELAYS = (2.0,)

# D40 — tolerancia para "push on-change": solo se pushea `update` si la
# estimación se movió más de este umbral desde el último push.
MIN_DELTA_SECONDS = 60


class Poller:
    """Procesa suscripciones activas y mantiene la estimacion fresca en cada device.

    Multi-sport (D47): recibe un dict de providers (`sport` -> `Provider`) y
    agrupa las suscripciones por `(sport, event_id)` para usar el provider
    correcto con cada liga/deporte.
    """

    def __init__(
        self,
        *,
        provider: Provider | None = None,
        providers: dict[str, Provider] | None = None,
        notifier: PushNotifier,
        state: AlertState,
        estimator: EstimatorEngine | None = None,
        retry_delays: tuple[float, ...] = RETRY_DELAYS,
        athlete_resolver: AthleteResolver | None = None,
    ) -> None:
        # Backward-compat: single provider (MMA) sigue funcionando.
        if providers is not None:
            self._providers = providers
        elif provider is not None:
            self._providers = {"mma": provider}
        else:
            raise ValueError("provider o providers es obligatorio")
        self._notifier = notifier
        self._state = state
        self._estimator = estimator or EstimatorEngine()
        self._retry_delays = retry_delays
        # Resolver se puede inicializar lazy con el primer provider.
        self._resolver = athlete_resolver

    async def poll_once(self, session: AsyncSession, now: datetime | None = None) -> int:
        """Procesa todas las suscripciones activas. Devuelve nº de pushes enviados."""
        now = now or datetime.now(UTC)
        pushed = 0

        result = await session.execute(
            sa.select(BoutSubscription).where(BoutSubscription.status == "active")
        )
        subs = result.scalars().all()

        # D47: agrupar por (sport, event_id) para usar el provider correcto.
        subs_by_key: dict[tuple[str, str], list[BoutSubscription]] = defaultdict(list)
        for sub in subs:
            subs_by_key[(sub.sport, sub.event_id)].append(sub)

        card_cache: dict[str, Card] = {}

        for (sport, event_id), event_subs in subs_by_key.items():
            provider = self._providers.get(sport)
            if provider is None:
                logger.warning(
                    "Provider no encontrado para sport=%s, saltando %d subs", sport, len(event_subs)
                )
                continue

            try:
                card = await self._load_card(provider, event_id, sport)
                card_cache[event_id] = card
            except Exception:
                logger.exception(
                    "Error cargando card del evento %s (sport=%s); saltando %d subs",
                    event_id,
                    sport,
                    len(event_subs),
                )
                continue

            device_ids = {s.device_id for s in event_subs}
            devices: dict[str, Device] = {}
            if device_ids:
                dres = await session.execute(sa.select(Device).where(Device.id.in_(device_ids)))
                for dev in dres.scalars().all():
                    devices[dev.id] = dev

            for sub in event_subs:
                try:
                    if await self._process_subscription(
                        session,
                        sub,
                        devices.get(sub.device_id),
                        card_cache[event_id],
                        now,
                        provider,
                    ):
                        pushed += 1
                except Exception:
                    logger.exception("Error procesando suscripcion %s", sub.id)

        return pushed

    async def _process_subscription(
        self,
        session: AsyncSession,
        sub: BoutSubscription,
        device: Device | None,
        card: Card,
        now: datetime,
        provider: Provider,
    ) -> bool:
        """Procesa una suscripcion. Devuelve True si se envio un push."""
        sub_id = sub.id
        bout_id = sub.bout_id
        event_id = sub.event_id
        sport = sub.sport

        if device is None or not device.is_active:
            logger.warning("Suscripción %s: device inexistente o inactivo, skip", sub_id)
            return False
        if not device.fcm_token:
            logger.warning("Suscripción %s: device sin fcm_token, no se puede pushear", sub_id)
            return False
        device_id = device.id
        device_token: str = device.fcm_token

        target = card.bout_by_id(bout_id)
        if target is None:
            logger.warning("Combate %s no encontrado en la card del evento %s", bout_id, event_id)
            return False

        # E3 — Guard del estado del combate objetivo.
        target_status_raw = await provider.get_competition_status(event_id, bout_id)
        target_state = target_status_raw.type.state
        if target_state == "in":
            return await self._send_status_push(session, sub, device, card, target, "started", now)
        if target_state == "post":
            return await self._send_status_push(
                session, sub, device, card, target, "cancelled", now
            )

        # target sigue en `pre` → estimar.
        prev = card.previous_bout(target)
        prev_bout_status: BoutStatus | None = None
        observed_at: datetime | None = None
        if prev is not None:
            prev_raw = await provider.get_competition_status(event_id, prev.id)
            prev_state = prev_raw.type.state
            prev_bout_status = BoutStatus(
                bout_id=prev.id,
                state=prev_state,
                clock=prev_raw.clock,
                period=prev_raw.period,
                completed=prev_raw.type.completed,
                sport=sport,
            )
            if prev_state == "post":
                # E2: anclar la transición in→post al primer momento observado.
                observed_at = await self._state.remember_transition(event_id, prev.id, now)

        # D45 — No pushear cuando el combate previo sigue en `pre` (no arrancó).
        # El primer push útil llega cuando el prev transiciona a `in` (lead>=30
        # dispara la alarma) o `post` (lead<30 dispara/reprograma). Pushear la
        # fecha oficial de ESPN aquí programaría la alarma local prematura —
        # el owner quiere "alarma solo cuando el backend detecte el inicio real".
        if prev is not None and prev_bout_status is not None and prev_bout_status.state == "pre":
            logger.debug(
                "Suscripción %s: previo en `pre`, sin info real; skip push",
                sub_id,
            )
            return False

        estimate = self._estimator.estimate(card, target, prev_bout_status, now, observed_at)

        # D40 push on-change: comparar con la última estimación pusheada.
        last = await self._state.get_last_estimate(sub_id, bout_id)
        if last is not None and abs((estimate.start_at - last).total_seconds()) < MIN_DELTA_SECONDS:
            logger.debug(
                "Suscripción %s: estimación no se movió (>=%ds desde último push), skip",
                sub_id,
                MIN_DELTA_SECONDS,
            )
            return False

        payload = AlertPayload(
            device_id=device_id,
            fcm_token=device_token,
            message_type="update",
            event_id=event_id,
            bout_id=bout_id,
            event_name=card.event_name,
            fighters=self._format_fighters(target),
            # D45: epoch millis (no ISO string) — la app Android parse con toLongOrNull().
            estimated_start_at=str(int(estimate.start_at.timestamp() * 1000)),
            minutes_until_start=max(0, int((estimate.start_at - now).total_seconds() // 60)),
            weight_class=target.weight_class,
        )
        result = await self._call_with_retries(payload)
        await self._log_alert(session, sub_id, device_id, bout_id, target, estimate, result, now, "update")

        if result.success:
            # E6: marcar idempotencia tras éxito (no antes de notificar).
            await self._state.set_last_estimate(sub_id, bout_id, estimate.start_at)
            await self._state.try_mark_fired(sub_id, bout_id, "update")
            logger.info(
                "Push 'update' enviado a device=%s para suscripción %s", device_id[:8], sub_id
            )
            return True

        logger.warning("Push 'update' fallido para suscripción %s: %s", sub_id, result.error)
        return False

    async def _send_status_push(
        self,
        session: AsyncSession,
        sub: BoutSubscription,
        device: Device,
        card: Card,
        target: Bout,
        msg_type: str,
        now: datetime,
    ) -> bool:
        """Envia un push `started`/`cancelled` (E3)."""
        sub_id = sub.id
        bout_id = sub.bout_id
        event_id = sub.event_id
        device_id = device.id
        device_token = device.fcm_token or ""

        if await self._state.was_fired(sub_id, bout_id, msg_type):
            logger.debug("Suscripcion %s: ya se envio '%s', skip", sub_id, msg_type)
            return False

        payload = AlertPayload(
            device_id=device_id,
            fcm_token=device_token,
            message_type=msg_type,  # type: ignore[arg-type]
            event_id=event_id,
            bout_id=bout_id,
            event_name=card.event_name,
            fighters=self._format_fighters(target),
            weight_class=target.weight_class,
        )
        result = await self._call_with_retries(payload)
        fake_estimate = EstimatedStart(
            bout_id=target.id, start_at=now, confidence="high", reason=msg_type
        )
        await self._log_alert(session, sub_id, device_id, bout_id, target, fake_estimate, result, now, msg_type)

        if result.success:
            await self._state.try_mark_fired(sub_id, bout_id, msg_type)
            logger.info(
                "Push '%s' enviado a device=%s para suscripcion %s",
                msg_type, device_id[:8], sub_id,
            )
            if msg_type == "cancelled":
                sub.status = "fired"
                await session.commit()
            return True
        return False

    def _format_fighters(self, target: Bout) -> str | None:
        red = target.red.name if target.red and target.red.name else None
        blue = target.blue.name if target.blue and target.blue.name else None
        if red and blue:
            return f"{red} vs {blue}"
        if red or blue:
            return red or blue
        return None

    async def _load_card(self, provider: Provider, event_id: str, sport: str = "mma") -> Card:
        """Carga la tarjeta del evento via Provider y mapea a dominio.

        Multi-sport (D47): resuelve nombres de atletas con AthleteResolver para
        MMA y con `competitor.name` inline para tenis (D49). Mapea `court` y
        `round` de tennis al dominio.
        """
        # Lazy-init del resolver con el primer provider (backward-compat)
        if self._resolver is None:
            self._resolver = AthleteResolver(provider)

        event = await provider.get_event_card(event_id)

        athlete_ids = [
            corner.athlete.athlete_id
            for comp in event.bouts
            for corner in (comp.red_corner, comp.blue_corner)
            if corner and corner.athlete and corner.athlete.athlete_id
        ]
        resolved = await self._resolver.resolve_many(athlete_ids)

        def _to_athlete(corner: ProviderCompetitor | None) -> Athlete | None:
            if corner is None:
                return None
            if corner.name:
                return Athlete(id=corner.id, name=corner.name)
            if corner.athlete is None:
                return None
            aid = corner.athlete.athlete_id
            if not aid:
                return None
            found = resolved.get(aid)
            return Athlete(id=aid, name=found.name if found else None)

        bouts: list[Bout] = []
        for comp in event.bouts:
            comp_date = comp.date
            if comp_date.endswith("Z"):
                comp_date = comp_date[:-1] + "+00:00"
            bouts.append(
                Bout(
                    id=comp.id,
                    match_number=comp.match_number,
                    date=datetime.fromisoformat(comp_date),
                    card_segment=comp.card_segment.name if comp.card_segment else None,
                    weight_class=comp.weight_class.text if comp.weight_class else None,
                    periods=comp.format.regulation.periods if comp.format else 3,
                    round_seconds=comp.format.regulation.clock if comp.format else 300.0,
                    red=_to_athlete(comp.red_corner),
                    blue=_to_athlete(comp.blue_corner),
                    sport=sport,
                    court=comp.court.description if comp.court else None,
                    round_description=comp.round.description if comp.round else None,
                )
            )
        return Card(event_id=event.id, event_name=event.name, bouts=bouts, sport=sport)

    async def _call_with_retries(self, payload: AlertPayload) -> PushResult:
        """Envía el push con reintentos cortos (E7: 1 retry de 2 s)."""
        last_result: PushResult = PushResult(success=False, error="no attempts")
        for attempt, delay in enumerate((0.0, *self._retry_delays)):
            if delay > 0:
                await asyncio.sleep(delay)
            logger.debug("Intento %d de push para device=%s", attempt + 1, payload.device_id[:8])
            last_result = await self._notifier.send(payload)
            if last_result.success:
                return last_result
        return last_result

    async def _log_alert(
        self,
        session: AsyncSession,
        sub_id: str,
        device_id: str,
        bout_id: str,
        target: Bout,
        estimate: EstimatedStart,
        result: PushResult,
        now: datetime,
        msg_type: str,
    ) -> None:
        """Registra el push en BD (alert_log) con idempotencia UNIQUE (E6)."""
        payload = json.dumps(
            {
                "message_type": msg_type,
                "bout_id": bout_id,
                "estimate_start": estimate.start_at.isoformat(),
                "confidence": estimate.confidence,
                "reason": estimate.reason,
                "weight_class": target.weight_class,
            },
            ensure_ascii=False,
        )
        log = AlertLog(
            id=str(uuid.uuid4()),
            subscription_id=sub_id,
            device_id=device_id,
            bout_id=bout_id,
            fired_at=now,
            fired_at_epoch_hour=int(now.timestamp()) // 3600,
            payload=payload,
            notifier_response=result.message_id or result.error,
            status="fired" if result.success else "failed",
            attempts=len(self._retry_delays) + 1,
        )
        try:
            session.add(log)
            await session.commit()
        except sa.exc.IntegrityError:
            logger.info("alert_log: duplicado evitado por UNIQUE (D16/E6) — msg=%s", msg_type)
            await session.rollback()
