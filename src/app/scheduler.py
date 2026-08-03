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
from datetime import timedelta
from typing import Any

import redis.asyncio as aioredis
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.db.session import SessionLocal
from app.domain.entities import Bout
from app.engine.estimator import EstimatorConfig, EstimatorEngine
from app.engine.poller import Poller
from app.engine.state import AlertState
from app.notifiers import get_notifier
from app.providers.athletes import AthleteResolver
from app.providers.base import Provider
from app.providers.espn_football import EspnFootballProvider
from app.providers.espn_nba import EspnNbaProvider
from app.providers.espn_nfl import EspnNflProvider
from app.providers.espn_tennis import EspnTennisProvider
from app.providers.espn_ufc import EspnUfcProvider
from app.providers.teams import TeamResolver

logger = logging.getLogger(__name__)


def _nba_buffer_for(target: Bout) -> timedelta | None:
    """D57: buffer asimetrico NBA. Q3 (target.match_number==3) requiere Q2->Q3
    halftime (15 min). El resto Q2/Q4 usa comercial corto (2 min). Otros
    deportes devuelven None y el estimator cae al buffer fijo (comportamiento
    pre-NBA); aportar None es equivalente a no definir `buffer_for`."""
    if target.sport != "nba":
        return None
    if target.match_number == 3:
        return timedelta(seconds=settings.buffer_nba_halftime_seconds)
    return timedelta(seconds=settings.buffer_nba_quarter_seconds)


def _nfl_buffer_for(target: Bout) -> timedelta | None:
    """D72: buffer asimetrico NFL. Q3 (target.match_number==3) requiere Q2->Q3
    halftime (~15 min). El resto Q2/Q4 usa comercial corto (2 min)."""
    if target.sport != "nfl":
        return None
    if target.match_number == 3:
        return timedelta(seconds=settings.buffer_nfl_halftime_seconds)
    return timedelta(seconds=settings.buffer_nfl_quarter_seconds)


def _football_buffer_for(target: Bout) -> timedelta | None:
    if target.sport != "football":
        return None
    return None


class PollerScheduler:
    """Ciclo de vida del scheduler + singletons del pipeline de alertas.

    Multi-sport (D47): mantiene un dict de providers (mma, tennis, nba) y un
    unico Poller que los recibe todos. D57: el estimador usa un callback
    `buffer_for` que selecciona el buffer segun el deporte del target.
    """

    def __init__(self) -> None:
        self._scheduler: AsyncIOScheduler | None = None
        self._providers: dict[tuple[str, str], Provider] = {}
        self._state: AlertState | None = None
        self._poller: Poller | None = None

    def _build(self) -> Poller:
        from app.api.routes.events import get_shared_http_client

        http_client = get_shared_http_client()
        self._providers[("mma", "")] = EspnUfcProvider(client=http_client)
        self._providers[("tennis", "atp")] = EspnTennisProvider(league="atp", client=http_client)
        self._providers[("tennis", "wta")] = EspnTennisProvider(league="wta", client=http_client)
        self._providers[("nba", "")] = EspnNbaProvider(league=settings.espn_nba_league, client=http_client)
        self._providers[("nfl", "")] = EspnNflProvider(league=settings.espn_nfl_league, client=http_client)
        for league in settings.football_leagues:
            self._providers[("football", league)] = EspnFootballProvider(league=league, client=http_client)
        if settings.app_env == "development":
            import fakeredis.aioredis as fakeredis_aio

            redis_client: Any = fakeredis_aio.FakeRedis(decode_responses=True)
            logger.info("Usando fakeredis para desarrollo local")
        else:
            redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._state = AlertState(client=redis_client)
        athlete_resolver = AthleteResolver(self._providers[("mma", "")], redis_client=redis_client)
        team_resolvers: dict[str, TeamResolver] = {}
        team_resolvers["nba"] = TeamResolver(
            self._providers[("nba", "")],
            redis_client=redis_client,
        )
        team_resolvers["nfl"] = TeamResolver(
            self._providers[("nfl", "")],
            redis_client=redis_client,
        )
        for league in settings.football_leagues:
            team_resolvers[league] = TeamResolver(
                self._providers[("football", league)],
                redis_client=redis_client,
            )

        def buffer_for(target: Bout) -> timedelta | None:
            nba_result = _nba_buffer_for(target)
            if nba_result is not None:
                return nba_result
            nfl_result = _nfl_buffer_for(target)
            if nfl_result is not None:
                return nfl_result
            return _football_buffer_for(target)

        estimator = EstimatorEngine(
            EstimatorConfig(
                buffer_intercombate_seconds=settings.buffer_intercombate_seconds,
                buffer_for=buffer_for,
            )
        )
        return Poller(
            providers=self._providers,
            notifier=get_notifier(),
            state=self._state,
            estimator=estimator,
            athlete_resolver=athlete_resolver,
            team_resolvers=team_resolvers,
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
        for provider in self._providers.values():
            try:
                await provider.aclose()
            except Exception:
                logger.exception("Error cerrando provider")
        self._providers = {}
        self._poller = None
        logger.info("Scheduler parado")


poller_scheduler = PollerScheduler()
