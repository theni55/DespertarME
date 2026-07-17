"""Scheduler in-process del Poller (MVP launch, D31).

Arranca un `AsyncIOScheduler` (APScheduler) dentro del proceso FastAPI
(lifespan) que ejecuta `Poller.poll_once` cada `poll_default_seconds`.

Requisito operativo: **1 solo worker de uvicorn**. Con varios workers el
poller correría duplicado (la idempotencia Redis + UNIQUE en BD lo mitigan,
pero el diseño del MVP es single-worker).

La cadencia adaptativa por estado (D15) queda como refinamiento futuro: el
intervalo fijo (default 60 s) es suficiente para precisión de minuto con
`lead_minutes >= 5`.
"""

from __future__ import annotations

import logging

import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db.session import SessionLocal
from app.engine.estimator import EstimatorConfig, EstimatorEngine
from app.engine.poller import Poller
from app.engine.state import AlertState
from app.notifiers import get_notifier
from app.providers.athletes import AthleteResolver
from app.providers.espn_ufc import EspnUfcProvider

logger = logging.getLogger(__name__)


class PollerScheduler:
    """Ciclo de vida del scheduler + singletons del pipeline de alertas."""

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None
        self._provider: EspnUfcProvider | None = None
        self._state: AlertState | None = None
        self._poller: Poller | None = None

    def _build(self) -> Poller:
        self._provider = EspnUfcProvider()
        redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._state = AlertState(client=redis_client)
        resolver = AthleteResolver(self._provider, redis_client=redis_client)
        # D45: pasar buffer_intercombate_seconds al EstimatorEngine para que
        # respete la configuración del `.env` (antes se hardcodeaba en 300s).
        estimator = EstimatorEngine(
            EstimatorConfig(buffer_intercombate_seconds=settings.buffer_intercombate_seconds)
        )
        return Poller(
            provider=self._provider,
            notifier=get_notifier(),
            state=self._state,
            estimator=estimator,
            athlete_resolver=resolver,
        )

    async def _poll_job(self) -> None:
        if self._poller is None:  # pragma: no cover - defensivo
            return
        try:
            async with SessionLocal() as session:
                fired = await self._poller.poll_once(session)
            if fired:
                logger.info("Poll completado: %d alertas disparadas", fired)
        except Exception:
            logger.exception("Error en el poll periódico")

    def start(self) -> None:
        if not settings.scheduler_enabled:
            logger.info("Scheduler deshabilitado por config (SCHEDULER_ENABLED=false)")
            return
        self._poller = self._build()
        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            self._poll_job,
            trigger="interval",
            seconds=settings.poll_default_seconds,
            id="poll_alerts",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=120,
        )
        self._scheduler.start()
        logger.info(
            "Scheduler arrancado: poll cada %d s (notifier según config)",
            settings.poll_default_seconds,
        )

    async def stop(self) -> None:
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
        if self._state is not None:
            await self._state.aclose()
            self._state = None
        if self._provider is not None:
            await self._provider.aclose()
            self._provider = None
        self._poller = None
        logger.info("Scheduler parado")


poller_scheduler = PollerScheduler()
