"""Tests del provider EspnNbaProvider con respx (mock httpx) — D56.

Cubre el checklist de la Fase NBA:
1. Listar eventos devuelve lista no vacia.
2. get_event_card sintetiza 4 quarters (Q1-Q4) con bout_id = `{eventId}_q{N}`.
3. get_competition_status deriva el estado por cuarto (pre/in/post) del status
   global del juego (period + state).
4. Circuit breaker abre tras N fallos consecutivos (reutiliza _is_retryable).
5. TeamResolver resuelve nombre + logo de un equipo NBA.
6. Los competitors remapean order 0/1 (home/away) -> 1/2 (red/blue corner).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.providers import CircuitBreakerOpenError, EspnNbaProvider
from app.providers.models import CompetitionStatus, Event, EventSummary, TeamDetail

BASE = "https://sports.core.api.espn.com/v2"
LEAGUE = "nba"
FIX_DIR = Path(__file__).parent / "fixtures" / "espn_nba"

EVENT_ID = "401898716"
TEAM_HOME_ID = "23"  # Sacramento Kings (home)
TEAM_AWAY_ID = "13"  # Los Angeles Lakers (away)


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIX_DIR / name).read_text(encoding="utf-8"))


def _events_list_url() -> str:
    return f"{BASE}/sports/basketball/leagues/{LEAGUE}/events?seasontype=2"


def _event_url(event_id: str = EVENT_ID) -> str:
    return f"{BASE}/sports/basketball/leagues/{LEAGUE}/events/{event_id}"


def _status_url(event_id: str = EVENT_ID) -> str:
    # NBA: competition_id == event_id.
    return f"{BASE}/sports/basketball/leagues/{LEAGUE}/events/{event_id}/competitions/{event_id}/status"


def _team_url(team_id: str) -> str:
    # El provider hace probing de years; mockeamos el year actual.
    import datetime as dt

    year = dt.datetime.now(dt.UTC).year
    return f"{BASE}/sports/basketball/leagues/{LEAGUE}/seasons/{year}/teams/{team_id}"


# --- Test 1: listar eventos devuelve lista no vacia ---------------------------


@respx.mock
async def test_list_upcoming_events_returns_non_empty_list() -> None:
    respx.get(url=_events_list_url()).respond(json=_load("event_list.json"))
    respx.get(url=_event_url()).respond(json=_load(f"event_{EVENT_ID}.json"))

    from datetime import UTC, datetime

    async with EspnNbaProvider() as provider:
        # Usamos min_date bajo para que el filtro no descarte fixtures preseason.
        summaries = await provider.list_upcoming_events(min_date=datetime(2026, 1, 1, tzinfo=UTC))

    assert len(summaries) >= 1
    first = summaries[0]
    assert isinstance(first, EventSummary)
    assert first.id == EVENT_ID
    assert "Lakers" in first.name or "Kings" in first.name


# --- Test 2: get_event_card sintetiza 4 quarters -----------------------------


@respx.mock
async def test_get_event_card_synthesizes_four_quarters() -> None:
    respx.get(url=_event_url()).respond(json=_load(f"event_{EVENT_ID}.json"))

    async with EspnNbaProvider() as provider:
        event = await provider.get_event_card(EVENT_ID)

    assert isinstance(event, Event)
    assert event.id == EVENT_ID
    # D56: 4 quarters sinteticos.
    assert len(event.bouts) == 4
    # match_number = 1..4 en orden.
    match_numbers = [b.match_number for b in event.bouts]
    assert match_numbers == [1, 2, 3, 4]
    # bout_id sintetico = `{eventId}_q{N}`.
    assert event.bouts[0].id == f"{EVENT_ID}_q1"
    assert event.bouts[3].id == f"{EVENT_ID}_q4"
    # cardSegment siempre "Regulation" (D56 no distingue main/prelims).
    for b in event.bouts:
        assert b.card_segment is not None
        assert b.card_segment.name == "Regulation"
    # format: un cuarto = 1 period de 720 segundos.
    assert event.bouts[0].format is not None
    assert event.bouts[0].format.regulation.periods == 1
    assert event.bouts[0].format.regulation.clock == 720.0


# --- Test 3: remapping de corners 0/1 -> 1/2 (red/blue) --------------------


@respx.mock
async def test_get_event_card_remaps_nba_competitor_order_to_red_blue() -> None:
    respx.get(url=_event_url()).respond(json=_load(f"event_{EVENT_ID}.json"))

    async with EspnNbaProvider() as provider:
        event = await provider.get_event_card(EVENT_ID)

    q1 = event.bouts[0]
    # Red corner = order 1 (originally home, order=0).
    assert q1.red_corner is not None
    assert q1.red_corner.order == 1
    # Blue corner = order 2 (originally away, order=1).
    assert q1.blue_corner is not None
    assert q1.blue_corner.order == 2
    # NBA: competitors llevan `team $ref` (no `athlete $ref`).
    assert q1.red_corner.team is not None
    assert q1.blue_corner.team is not None
    assert q1.red_corner.athlete is None
    assert q1.blue_corner.athlete is None
    # Team ids se extraen del $ref.
    assert q1.red_corner.team.team_id == TEAM_HOME_ID  # Sacramento Kings
    assert q1.blue_corner.team.team_id == TEAM_AWAY_ID  # Los Angeles Lakers


# --- Test 4: derivacion de per-quarter status desde el global -----------------


@respx.mock
async def test_get_competition_status_pre_when_game_not_started() -> None:
    """period=0 → todos los cuartos estan en pre."""
    respx.get(url=_status_url()).respond(json=_load("competition_status_pre.json"))
    async with EspnNbaProvider() as provider:
        for q in (1, 2, 3, 4):
            status = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q{q}")
            assert isinstance(status, CompetitionStatus)
            assert status.type.state == "pre"
            assert status.period == q
            assert status.type.completed is False


@respx.mock
async def test_get_competition_status_in_q1_marks_q1_in_others_pre_post() -> None:
    """period=1, state=in → Q1 en `in`; Q2-Q4 en `pre`."""
    respx.get(url=_status_url()).respond(json=_load("competition_status_in_q1.json"))
    async with EspnNbaProvider() as provider:
        q1 = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q1")
        assert q1.type.state == "in"
        assert q1.period == 1
        # Clock y estado global pasan al Q1 en curso.
        assert q1.clock == 600.0
        for q in (2, 3, 4):
            other = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q{q}")
            assert other.type.state == "pre"
            assert other.period == q


@respx.mock
async def test_get_competition_status_in_q2_marks_q1_post_q2_in_others_pre() -> None:
    """period=2, state=in → Q1 en `post`; Q2 en `in`; Q3-Q4 en `pre`."""
    respx.get(url=_status_url()).respond(json=_load("competition_status_in_q2.json"))
    async with EspnNbaProvider() as provider:
        q1 = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q1")
        assert q1.type.state == "post"
        assert q1.type.completed is True
        q2 = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q2")
        assert q2.type.state == "in"
        assert q2.period == 2
        for q in (3, 4):
            other = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q{q}")
            assert other.type.state == "pre"


@respx.mock
async def test_get_competition_status_in_q3_marks_q1q2_post_q3_in() -> None:
    """period=3, state=in → Q1, Q2 en `post`; Q3 en `in`; Q4 en `pre`."""
    respx.get(url=_status_url()).respond(json=_load("competition_status_in_q3.json"))
    async with EspnNbaProvider() as provider:
        for q in (1, 2):
            post = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q{q}")
            assert post.type.state == "post"
        q3 = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q3")
        assert q3.type.state == "in"
        q4 = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q4")
        assert q4.type.state == "pre"


@respx.mock
async def test_get_competition_status_in_q4_marks_only_q4_in() -> None:
    """period=4, state=in → Q1-Q3 en `post`; Q4 en `in`."""
    respx.get(url=_status_url()).respond(json=_load("competition_status_in_q4.json"))
    async with EspnNbaProvider() as provider:
        for q in (1, 2, 3):
            post = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q{q}")
            assert post.type.state == "post"
        q4 = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q4")
        assert q4.type.state == "in"


@respx.mock
async def test_get_competition_status_post_marks_all_quarters_post() -> None:
    """period=4, state=post (game ended after Q4) → todos en `post`."""
    respx.get(url=_status_url()).respond(json=_load("competition_status_post.json"))
    async with EspnNbaProvider() as provider:
        for q in (1, 2, 3, 4):
            post = await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q{q}")
            assert post.type.state == "post"


@respx.mock
async def test_get_competition_status_caches_global_status_within_poll() -> None:
    """El cache evita llamar a ESPN multiples veces en llamadas consecutivas."""
    route = respx.get(url=_status_url()).respond(json=_load("competition_status_in_q2.json"))
    async with EspnNbaProvider() as provider:
        # 4 llamadas al status endpoint para Q1-Q4, todas derivan del mismo
        # status global. Sin cache -> 4 fetches; con cache -> 1 fetch.
        for q in (1, 2, 3, 4):
            await provider.get_competition_status(EVENT_ID, f"{EVENT_ID}_q{q}")
    assert route.call_count == 1, f"esperado 1 call, fueron {route.call_count}"


# --- Test 5: Circuit breaker (reutiliza _is_retryable desde espn_ufc) --------


@respx.mock
async def test_circuit_breaker_opens_after_n_failures() -> None:
    # 404 no cuenta (E5); solo 5xx abren el circuito.
    route = respx.get(url=_event_url()).mock(
        side_effect=httpx.Response(status_code=503, json={"error": "boom"})
    )
    async with EspnNbaProvider(max_retries=1, cb_fails=3, cb_open_seconds=60) as provider:
        # 3 fallos abren; el 4o levanta CircuitBreakerOpen sin tocar la red.
        for _ in range(3):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_event_card(EVENT_ID)
        assert provider.is_circuit_open is True
        with pytest.raises(CircuitBreakerOpenError):
            await provider.get_event_card(EVENT_ID)
    # El 4o intento (con circuito abierto) no llega a la red.
    assert route.call_count == 3


@respx.mock
async def test_circuit_breaker_4xx_does_not_open() -> None:
    """5 requests 404 no abren el CB (E5); cada una lanza 404 directamente."""
    route = respx.get(url=_event_url()).mock(
        side_effect=httpx.Response(status_code=404, json={"error": "no"})
    )
    async with EspnNbaProvider(max_retries=1, cb_fails=3, cb_open_seconds=60) as provider:
        for _ in range(5):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_event_card(EVENT_ID)
        assert provider.is_circuit_open is False
    # 5 calls fueron hechas (sin retry, sin circuito).
    assert route.call_count == 5


# --- Test 6: TeamResolver resuelve nombre + logo ----------------------------


@respx.mock
async def test_get_team_returns_display_name_and_logo() -> None:
    respx.get(url=_team_url(TEAM_HOME_ID)).respond(json=_load(f"team_{TEAM_HOME_ID}.json"))
    async with EspnNbaProvider() as provider:
        detail = await provider.get_team(TEAM_HOME_ID)
    assert isinstance(detail, TeamDetail)
    assert detail.id == TEAM_HOME_ID
    assert "Sacramento" in detail.display_name or "Kings" in detail.display_name
    # Logos[]馨eres非 vacio.
    assert detail.logos
    assert detail.logo_url is not None


@respx.mock
async def test_team_resolver_caches_after_first_fetch() -> None:
    route = respx.get(url=_team_url(TEAM_HOME_ID)).respond(json=_load(f"team_{TEAM_HOME_ID}.json"))
    from app.providers import EspnNbaProvider
    from app.providers.teams import TeamResolver

    async with EspnNbaProvider() as provider:
        resolver = TeamResolver(provider)
        r1 = await resolver.resolve(TEAM_HOME_ID)
        r2 = await resolver.resolve(TEAM_HOME_ID)
    assert r1.name == r2.name
    # Solo 1 fetch a ESPN (memoria cachea el segundo).
    assert route.call_count == 1


@respx.mock
async def test_team_resolver_degrades_to_tbd_on_failure() -> None:
    respx.get(url=_team_url(TEAM_HOME_ID)).mock(
        side_effect=httpx.Response(status_code=500, json={"error": "boom"})
    )
    from app.providers.teams import TeamResolver

    async with EspnNbaProvider(max_retries=1) as provider:
        resolver = TeamResolver(provider)
        r = await resolver.resolve(TEAM_HOME_ID)
    assert r.name is None
    assert r.display == "TBD"


# --- Test 7: Estimador NBA con buffer asimetrico -----------------------------


async def test_estimator_nba_q2_uses_quarter_buffer_when_prev_post() -> None:
    """D57: prev Q1 en post + target Q2 → start = observed_at + 120s (no 600s)."""
    from datetime import UTC, datetime, timedelta

    from app.config import settings
    from app.domain.entities import Athlete, Bout, BoutStatus, Card
    from app.engine.estimator import EstimatorConfig, EstimatorEngine

    def buffer_for(target: Bout) -> timedelta | None:
        if target.sport != "nba":
            return None
        if target.match_number == 3:
            return timedelta(seconds=settings.buffer_nba_halftime_seconds)
        return timedelta(seconds=settings.buffer_nba_quarter_seconds)

    estimator = EstimatorEngine(
        EstimatorConfig(
            buffer_intercombate_seconds=settings.buffer_intercombate_seconds,
            buffer_for=buffer_for,
        )
    )

    now = datetime(2026, 10, 5, 4, 0, tzinfo=UTC)
    observed_at = now  # Q1 acaba "ahora"
    q1 = Bout(
        id=f"{EVENT_ID}_q1",
        match_number=1,
        date=now,
        periods=1,
        round_seconds=720.0,
        sport="nba",
        red=Athlete(id="home"),
        blue=Athlete(id="away"),
    )
    q2 = Bout(
        id=f"{EVENT_ID}_q2",
        match_number=2,
        date=now + timedelta(minutes=15),
        periods=1,
        round_seconds=720.0,
        sport="nba",
    )
    q3 = Bout(
        id=f"{EVENT_ID}_q3",
        match_number=3,
        date=now + timedelta(minutes=30),
        periods=1,
        round_seconds=720.0,
        sport="nba",
    )
    card = Card(event_id=EVENT_ID, event_name="Lakers @ Kings", bouts=[q1, q2, q3], sport="nba")
    # Q2 previo: Q1 post. Q3 previo: Q2 post (no Q1).
    prev_q1 = BoutStatus(
        bout_id=q1.id, state="post", period=1, completed=True, observed_at=observed_at, sport="nba"
    )

    est_q2 = estimator.estimate(card, q2, prev_q1, now=now, observed_at=observed_at)
    # Q2: observed_at + 120s (Q1→Q2 comercial corto).
    assert est_q2.start_at == observed_at + timedelta(seconds=settings.buffer_nba_quarter_seconds)

    # Q3 previo: Q2 post en observed_q2. observed_q2 != observed_q1.
    observed_q2 = observed_at + timedelta(minutes=15)  # Q2 acaba 15 min despues
    prev_q2 = BoutStatus(
        bout_id=q2.id, state="post", period=2, completed=True, observed_at=observed_q2, sport="nba"
    )
    est_q3 = estimator.estimate(card, q3, prev_q2, now=observed_q2, observed_at=observed_q2)
    # Q3: observed_q2 + 900s (halftime Q2→Q3).
    assert est_q3.start_at == observed_q2 + timedelta(seconds=settings.buffer_nba_halftime_seconds)


async def test_estimator_nba_q2_when_prev_in_uses_quarter_buffer() -> None:
    """D57: prev Q1 en `in` + target Q2 → start = now + remaining + buffer_q2."""
    from datetime import UTC, datetime, timedelta

    from app.config import settings
    from app.domain.entities import Bout, BoutStatus, Card
    from app.engine.estimator import EstimatorConfig, EstimatorEngine

    def buffer_for(target: Bout) -> timedelta | None:
        if target.sport != "nba":
            return None
        if target.match_number == 3:
            return timedelta(seconds=settings.buffer_nba_halftime_seconds)
        return timedelta(seconds=settings.buffer_nba_quarter_seconds)

    estimator = EstimatorEngine(
        EstimatorConfig(
            buffer_intercombate_seconds=settings.buffer_intercombate_seconds,
            buffer_for=buffer_for,
        )
    )

    now = datetime(2026, 10, 5, 4, 0, tzinfo=UTC)
    q1 = Bout(
        id=f"{EVENT_ID}_q1",
        match_number=1,
        date=now,
        periods=1,
        round_seconds=720.0,
        sport="nba",
    )
    q2 = Bout(
        id=f"{EVENT_ID}_q2",
        match_number=2,
        date=now + timedelta(minutes=15),
        periods=1,
        round_seconds=720.0,
        sport="nba",
    )
    card = Card(event_id=EVENT_ID, event_name="Lakers @ Kings", bouts=[q1, q2], sport="nba")
    # Q1 en `in`, period=1, clock=600 (10 min remaining of 12:00).
    elapsed = (1 - 1) * 720.0 + (720.0 - 600.0)  # = 120s jugados
    prev_status = BoutStatus(
        bout_id=q1.id, state="in", clock=600.0, period=1, completed=False, sport="nba"
    )
    assert prev_status.elapsed_seconds == elapsed

    est_q2 = estimator.estimate(card, q2, prev_status, now=now)
    # remaining = q1.duration (720) - elapsed (120) = 600; buffer_q2 = 120
    expected = now + timedelta(seconds=600) + timedelta(seconds=settings.buffer_nba_quarter_seconds)
    assert est_q2.start_at == expected


async def test_estimator_mma_uses_default_buffer_when_buffer_for_returns_none() -> None:
    """Regression: MMA/Tenis behavior unchanged when `buffer_for` returns None."""
    from datetime import UTC, datetime, timedelta

    from app.config import settings
    from app.domain.entities import Bout, BoutStatus, Card
    from app.engine.estimator import EstimatorConfig, EstimatorEngine

    # Callback que devuelve None para todo sport != nba (simula el scheduler).
    def buffer_for(target: Bout) -> timedelta | None:
        if target.sport != "nba":
            return None
        return timedelta(seconds=settings.buffer_nba_quarter_seconds)

    estimator = EstimatorEngine(
        EstimatorConfig(
            buffer_intercombate_seconds=600,
            buffer_for=buffer_for,
        )
    )
    now = datetime(2026, 7, 11, 21, 0, tzinfo=UTC)
    b14 = Bout(id="b14", match_number=14, date=now, periods=3, round_seconds=300.0, sport="mma")
    b13 = Bout(id="b13", match_number=13, date=now, periods=3, round_seconds=300.0, sport="mma")
    card = Card(event_id="ev", event_name="UFC", bouts=[b13, b14], sport="mma")
    # En UFC mn desciende con el tiempo: mn14 (prelims 1) ocurre primero, mn1
    # es el main event = ultimo. `previous_bout(b13)` -> mn14 -> b14.
    # target=b13 (mn13), prev=b14 (mn14) en post.
    prev = BoutStatus(bout_id=b14.id, state="post", period=3, completed=True, sport="mma")
    est = estimator.estimate(card, b13, prev, now=now, observed_at=now)
    # MMA buffer fijo 600s (callback devolvio None para sport != nba).
    assert est.start_at == now + timedelta(seconds=600)


# --- Test 8: schemas aceptan lead=0 solo NBA Q2-Q4 -------------------------


def test_schemas_accept_lead_zero_for_nba_q2_q4() -> None:
    from app.api.schemas import BoutSubscriptionCreate

    for q in (2, 3, 4):
        body = BoutSubscriptionCreate(
            event_id=EVENT_ID,
            bout_id=f"{EVENT_ID}_q{q}",
            target_match_number=q,
            lead_minutes=0,
            sport="nba",
        )
        body.validate_for_sport()  # no exception


def test_schemas_reject_lead_zero_for_mma() -> None:

    from app.api.schemas import BoutSubscriptionCreate

    body = BoutSubscriptionCreate(
        event_id="ev",
        bout_id="b1",
        target_match_number=1,
        lead_minutes=0,
        sport="mma",
    )
    # El validator contextual (no pydantic) debe rechazar.
    import pytest

    with pytest.raises(ValueError):
        body.validate_for_sport()


def test_schemas_reject_negative_lead() -> None:
    from pydantic import ValidationError

    from app.api.schemas import BoutSubscriptionCreate

    with pytest.raises(ValidationError):
        BoutSubscriptionCreate(
            event_id="ev",
            bout_id="b1",
            target_match_number=1,
            lead_minutes=-1,
            sport="mma",
        )


def test_schemas_reject_nba_q2_with_lead_above_zero() -> None:
    """NBA Q2-Q4 requiere exactamente lead_minutes=0."""
    from app.api.schemas import BoutSubscriptionCreate

    body = BoutSubscriptionCreate(
        event_id=EVENT_ID,
        bout_id=f"{EVENT_ID}_q2",
        target_match_number=2,
        lead_minutes=10,
        sport="nba",
    )
    import pytest

    with pytest.raises(ValueError):
        body.validate_for_sport()


# --- Test 9: domain Bout/ BoutStatus NBA -------------------------------------


def test_bout_nba_estimated_duration_is_quarter_seconds() -> None:
    from datetime import UTC, datetime

    from app.domain.entities import Bout

    b = Bout(
        id="x_q1",
        match_number=1,
        date=datetime.now(UTC),
        periods=1,
        round_seconds=720.0,
        sport="nba",
    )
    # D56: un cuarto = 1 period de 720s (sin descanso intercuarto aqui).
    assert b.estimated_duration_seconds == 720.0


def test_bout_status_nba_elapsed_when_in_q1_clock_600() -> None:
    """Q1 en in, clock=600 (10 min remaining of 12:00) → elapsed = 120."""
    from app.domain.entities import BoutStatus

    status = BoutStatus(bout_id="x_q1", state="in", clock=600.0, period=1, sport="nba")
    assert status.elapsed_seconds == 120.0


def test_bout_status_nba_elapsed_when_in_q2_clock_300() -> None:
    """Q2 en in, clock=300 (5 min remaining of Q2 12:00) → elapsed = (1)*720 + 420 = 1140."""
    from app.domain.entities import BoutStatus

    status = BoutStatus(bout_id="x_q2", state="in", clock=300.0, period=2, sport="nba")
    assert status.elapsed_seconds == 720.0 + (720.0 - 300.0)


def test_bout_status_nba_elapsed_zero_when_not_in() -> None:
    from app.domain.entities import BoutStatus

    pre = BoutStatus(bout_id="x_q1", state="pre", period=0, sport="nba")
    assert pre.elapsed_seconds == 0.0
    post = BoutStatus(bout_id="x_q1", state="post", period=1, sport="nba")
    assert post.elapsed_seconds == 0.0
