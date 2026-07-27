"""Provider de ESPN Core API para NBA (D56).

Modelo "Bout = Cuarto" (D56): cada partido NBA se sintetiza como una Card
de 4 Bouts Q1-Q4. ESPN expone SOLO el estado global del partido (state +
period + clock); no expone estado pre/in/post por cuartos. Ergo el provider
deriva el estado de cada cuarto comparando el `period` global vs el quarter
objetivo.

Endpoints (verificados en vivo, Sesion NBA):
- `GET /sports/basketball/leagues/{league}/events?seasontype=2` → lista de partidos.
- `GET /sports/basketball/leagues/{league}/events/{id}` → partido con 1 competition.
- `GET /sports/basketball/leagues/{league}/events/{id}/competitions/{cId}/status`
  → estado global del partido (`clock`, `period`, `type.state`). Para NBA,
  `competition_id == event_id`.
- `GET /sports/basketball/leagues/nba/seasons/{year}/teams/{id}` → team
  detail (`displayName`, `logos[]`).

Diferencias clave con MMA/Tenis (D56):
- 1 competition por evento → sintetizamos 4 competitions Q1-Q4 con
  `Bout.id = "{eventId}_q{N}"`, `matchNumber = N`.
- Competitors tienen `team $ref` (no `athlete $ref`): los nombres se
  resuelven via `TeamResolver` (D58), no `AthleteResolver`.
- ESPN competitor `order` es 0 (home) / 1 (away); remapeamos a 1 (red) /
  2 (blue) para encajar con `Bout.red_corner`/`blue_corner`.
- `get_competition_status(event_id, competition_id)` ignora el
  `competition_id` (NBA tiene 1 solo por event) y cachea el status global
  3 s en memoria para evitar llamadas duplicadas dentro del mismo poll
  cycle (target + prev comparten el mismo endpoint).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any, cast
from urllib.parse import urlparse

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import settings
from app.providers.base import Provider
from app.providers.espn_ufc import CircuitBreakerOpenError, _is_retryable
from app.providers.models import (
    CompetitionStatus,
    Event,
    EventSummary,
    TeamDetail,
)

logger = logging.getLogger(__name__)

_EVENT_ID_RE = re.compile(r"/events/(\d+)")
_QUARTER_RE = re.compile(r"_q(\d+)$")

# Cache en memoria del status global por event_id: (timestamp, status_dict).
# TTL corto (3s) para dedupe llamadas dentro del mismo poll cycle sin servir
# data stalada entre ciclos.
_STATUS_CACHE_TTL = 3.0


def _event_id_from_ref(ref: str) -> str | None:
    if not ref:
        return None
    path = urlparse(ref).path
    m = _EVENT_ID_RE.search(path)
    return m.group(1) if m else None


def _parse_event_date(raw: str) -> datetime:
    value = raw
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


class EspnNbaProvider(Provider):
    """Provider concreto para ESPN Core API (NBA)."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        league: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        cb_fails: int | None = None,
        cb_open_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self._base_url = (base_url or settings.espn_base_url).rstrip("/")
        self._league = league or settings.espn_nba_league
        self._timeout = timeout if timeout is not None else settings.espn_timeout_seconds
        self._max_retries = max_retries if max_retries is not None else settings.espn_max_retries
        self._cb_fails = cb_fails if cb_fails is not None else settings.espn_circuit_breaker_fails
        self._cb_open_seconds = (
            cb_open_seconds
            if cb_open_seconds is not None
            else settings.espn_circuit_breaker_open_seconds
        )
        self._client = client or httpx.AsyncClient(timeout=self._timeout)
        self._owns_client = client is None
        self._clock = clock or time.monotonic
        self._consecutive_failures = 0
        self._open_until: float = 0.0
        # Cache en memoria del estado global: event_id -> (expira_en, status dict).
        self._status_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> EspnNbaProvider:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    # --- Circuit breaker -------------------------------------------------

    def _check_circuit(self) -> None:
        if self._clock() < self._open_until:
            raise CircuitBreakerOpenError(
                f"Circuit breaker abierto hasta {self._open_until:.1f}s "
                f"(fails={self._cb_fails}, open={self._cb_open_seconds}s)"
            )

    def _on_success(self) -> None:
        if self._consecutive_failures or self._open_until:
            logger.debug("Circuit breaker reset tras exito")
        self._consecutive_failures = 0
        self._open_until = 0.0

    def _on_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._cb_fails:
            self._open_until = self._clock() + self._cb_open_seconds
            self._consecutive_failures = 0
            logger.warning(
                "Circuit breaker ABIERTO por %ss tras %s fallos consecutivos",
                self._cb_open_seconds,
                self._cb_fails,
            )

    @property
    def is_circuit_open(self) -> bool:
        return self._clock() < self._open_until

    # --- HTTP con tenacity + circuit breaker -----------------------------

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    async def _request(self, url: str) -> dict[str, Any]:
        self._check_circuit()
        try:
            data = await self._request_with_retry(url)
        except Exception as exc:
            if _is_retryable(exc):
                self._on_failure()
            raise
        self._on_success()
        return data

    async def _request_with_retry(self, url: str) -> dict[str, Any]:
        retrying = AsyncRetrying(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential_jitter(initial=1, max=60),
            retry=retry_if_exception(_is_retryable),
            reraise=True,
        )
        async for attempt in retrying:
            with attempt:
                response = await self._client.get(url)
                response.raise_for_status()
                return cast(dict[str, Any], response.json())
        raise RuntimeError("retry loop exited without a result")

    # --- Contrato Provider (base.py) -------------------------------------

    async def list_upcoming_events(
        self, *, min_date: datetime | None = None, max_concurrent: int = 4
    ) -> Sequence[EventSummary]:
        list_url = self._url(f"/sports/basketball/leagues/{self._league}/events?seasontype=2")
        data = await self._request(list_url)
        ids: list[str] = []
        for item in data.get("items", []):
            ref = item.get("$ref", "")
            eid = _event_id_from_ref(ref)
            if eid:
                ids.append(eid)

        sem = asyncio.Semaphore(max_concurrent)

        async def _fetch_summary(eid: str) -> EventSummary | None:
            url = self._url(f"/sports/basketball/leagues/{self._league}/events/{eid}")
            async with sem:
                try:
                    ev_data = await self._request(url)
                except Exception:
                    logger.warning("No se pudo cargar resumen del partido %s", eid)
                    return None
            return EventSummary(
                id=ev_data["id"],
                name=ev_data.get("name", ""),
                date=ev_data.get("date", ""),
            )

        raw_summaries = await asyncio.gather(*(_fetch_summary(eid) for eid in ids))
        summaries = [s for s in raw_summaries if s is not None]

        cutoff = min_date or datetime.now(UTC)
        upcoming: list[EventSummary] = []
        for s in summaries:
            try:
                ev_dt = _parse_event_date(s.date)
            except ValueError:
                logger.warning("Fecha invalida en partido %s: %s", s.id, s.date)
                continue
            if ev_dt >= cutoff:
                upcoming.append(s)
        upcoming.sort(key=lambda x: x.date)
        return upcoming

    async def get_event_card(self, event_id: str) -> Event:
        """Sintetiza un Event NBA con 4 competitions Q1-Q4 (D56).

        NBA tiene 1 solo `competition` por evento (1 partido = 1 competition).
        Remapeamos `order` 0/1 (home/away) -> 1/2 (red/blue corner) y creamos
        4 competitions sinteticas, una por cuarto, preservando teams y metadata.
        `Bout.id = "{eventId}_q{N}"`, `matchNumber = N`.
        """
        url = self._url(f"/sports/basketball/leagues/{self._league}/events/{event_id}")
        data = await self._request(url)
        return self._synthesize_quarter_card(event_id, data)

    @staticmethod
    def _synthesize_quarter_card(event_id: str, data: dict[str, Any]) -> Event:
        competitions = data.get("competitions") or []
        if not competitions:
            return Event.model_validate(data)
        real_comp = competitions[0]
        real_competitors = real_comp.get("competitors") or []
        # Remapear order NBA (0=home, 1=away) -> 1=red, 2=blue corner.
        remapped_competitors = [
            {
                **c,
                "order": 1 if c.get("order") == 0 else 2,
            }
            for c in real_competitors
        ]
        regulation = (real_comp.get("format") or {}).get("regulation") or {}
        clock_per_quarter = regulation.get("clock", 720.0)
        type_obj = real_comp.get("type")
        synthetic_competitions: list[dict[str, Any]] = []
        for q in range(1, 5):  # Q1, Q2, Q3, Q4
            quarter_comp = {
                "id": f"{event_id}_q{q}",
                "matchNumber": q,
                "date": data.get("date", ""),
                "type": type_obj,
                "cardSegment": {"name": "Regulation", "description": "Regular season quarter"},
                "format": {
                    "regulation": {"periods": 1, "clock": clock_per_quarter},
                },
                "competitors": remapped_competitors,
            }
            synthetic_competitions.append(quarter_comp)
        synthetic_data = {**data, "competitions": synthetic_competitions}
        return Event.model_validate(synthetic_data)

    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        """Deriva el status de UN cuartel especifico a partir del status global.

        NBA: `competition_id == event_id` en ESPN. Aqui `competition_id` puede
        ser el bout_id sintetico `"{eventId}_q{N}"` (en el poller, target y prev
        usan bout_id como argumento). El cuarto N se extrae via regex.

        Logica de derivacion:
        - N > global.period: quarter aun no empezo → state=pre.
        - N == global.period AND global.state == in: este cuarto en curso.
        - N == global.period AND global.state == pre: todo el juego en pre.
        - N == global.period AND global.state == post: juego acabo en este cuarto.
        - N < global.period: este cuarto ya termino → state=post.
        """
        # Extraer el numero de quarter del bout_id sintetico.
        m = _QUARTER_RE.search(competition_id or "")
        quarter_n = int(m.group(1)) if m else 0
        global_status = await self._fetch_global_status_cached(event_id)
        return self._derive_quarter_status(quarter_n, global_status)

    async def _fetch_global_status_cached(self, event_id: str) -> dict[str, Any]:
        """Fetch con cache en memoria de 3 s para evitar duplicar dentro del poll."""
        now_mono = self._clock()
        cached = self._status_cache.get(event_id)
        if cached is not None and cached[0] > now_mono:
            return cached[1]
        url = self._url(
            f"/sports/basketball/leagues/{self._league}/events/{event_id}"
            f"/competitions/{event_id}/status"
        )
        data = await self._request(url)
        self._status_cache[event_id] = (now_mono + _STATUS_CACHE_TTL, data)
        return data

    @staticmethod
    def _derive_quarter_status(
        quarter_n: int, global_status_data: dict[str, Any]
    ) -> CompetitionStatus:
        """Traduce el status global del juego a un status sintetico del quarter N."""
        g_state = (global_status_data.get("type") or {}).get("state", "pre")
        g_period = int(global_status_data.get("period", 0) or 0)

        if quarter_n == 0:
            # Sin quarter especificado -> devolver el status global crudo.
            return CompetitionStatus.model_validate(global_status_data)

        def _synth(state: str, *, completed: bool) -> CompetitionStatus:
            return CompetitionStatus.model_validate(
                {
                    "clock": 0.0,
                    "displayClock": "0.0",
                    "period": quarter_n,
                    "type": {
                        "state": state,
                        "completed": completed,
                        "description": "Scheduled" if state == "pre" else "Final",
                        "shortDetail": "TBD" if state == "pre" else "Final",
                    },
                }
            )

        if g_period == 0:
            # Juego no ha empezado.
            return _synth("pre", completed=False)
        if quarter_n < g_period:
            # Este quarter ya paso.
            return _synth("post", completed=True)
        if quarter_n > g_period:
            # Este quarter no ha empezado todavia.
            return _synth("pre", completed=False)
        # quarter_n == g_period: este es el cuarto en curso (o el ultimo si post).
        if g_state == "pre":
            return _synth("pre", completed=False)
        # in o post: el cuarto coincide con el estado global.
        return CompetitionStatus.model_validate(global_status_data)

    async def get_athlete(self, athlete_id: str) -> Any:  # noqa: ANN401
        """NBA no usa `athlete $ref`; los nombres se resuelven via `get_team`
        y `TeamResolver`. Mantenemos el metodo por compatibilidad con el ABC
        pero lanza NotImplementedError si alguien lo llama por error."""
        raise NotImplementedError("NBA usa get_team, no get_athlete")

    async def get_team(self, team_id: str) -> TeamDetail:
        """Detalle de un equipo NBA. El endpoint cuelga de `/seasons/{year}/teams/{id}`,
        pero el ano depende de la URL del `$ref` original. Para no acoplar al
        provider al ano, hacemos probing: probamos el ano actual y el siguiente
        (ESPN expone el equipo en cualquier season con el mismo id).
        """
        # Intentamos primero la season mas reciente conocida via el endpoint
        # generico `/sports/basketball/leagues/nba/seasons/{year}/teams/{id}`.
        # Como fallback, probamos varios anos.
        years = [datetime.now(UTC).year, datetime.now(UTC).year + 1, datetime.now(UTC).year - 1]
        last_exc: Exception | None = None
        for year in years:
            url = self._url(
                f"/sports/basketball/leagues/{self._league}/seasons/{year}/teams/{team_id}"
            )
            try:
                data = await self._request(url)
                return TeamDetail.model_validate(data)
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code == 404:
                    continue
                raise
            except Exception as exc:
                last_exc = exc
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"No se pudo resolver el equipo {team_id} en ninguna season")
