"""Tests del provider EspnFootballProvider con respx (mock httpx) — D65.

Cubre el checklist de la Fase Football MVP:
1. Listar eventos devuelve lista no vacia.
2. get_event_card devuelve 1 bout con 2 competidores (home/away) con team $ref.
3. get_competition_status devuelve estado pre (period=0, state=pre).
4. Circuit breaker no abre en 4xx (reutiliza _is_retryable).
5. TeamResolver resuelve nombre + logo de un equipo de football.
6. get_team con probing de years.
"""

from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.providers import CircuitBreakerOpenError, EspnFootballProvider
from app.providers.models import CompetitionStatus, Event, EventSummary, TeamDetail

BASE = "https://sports.core.api.espn.com/v2"
LEAGUE = "esp.1"
FIX_DIR = Path(__file__).parent / "fixtures" / "espn_football"

EVENT_ID = "401882926"
TEAM_HOME_ID = "96"  # Alaves (home)
TEAM_AWAY_ID = "2922"  # Getafe (away)


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIX_DIR / name).read_text(encoding="utf-8"))


def _events_list_url() -> str:
    return f"{BASE}/sports/soccer/leagues/{LEAGUE}/events"


def _event_url(event_id: str = EVENT_ID) -> str:
    return f"{BASE}/sports/soccer/leagues/{LEAGUE}/events/{event_id}"


def _status_url(event_id: str = EVENT_ID, competition_id: str = "") -> str:
    cid = competition_id or event_id
    return f"{BASE}/sports/soccer/leagues/{LEAGUE}/events/{event_id}" f"/competitions/{cid}/status"


def _team_url(team_id: str) -> str:
    import datetime as dt

    year = dt.datetime.now(dt.UTC).year
    return f"{BASE}/sports/soccer/leagues/{LEAGUE}/seasons/{year}/teams/{team_id}"


def _team_url_alt_year(team_id: str, year: int) -> str:
    return f"{BASE}/sports/soccer/leagues/{LEAGUE}/seasons/{year}/teams/{team_id}"


# --- Test 1: listar eventos devuelve lista no vacia ---------------------------


@respx.mock
async def test_list_upcoming_events() -> None:
    respx.get(url=_events_list_url()).respond(json=_load("event_list.json"))
    respx.get(url=_event_url()).respond(json=_load(f"event_{EVENT_ID}.json"))
    respx.get(url=_event_url("401882918")).respond(
        json=_load("event_401882926.json")  # reuse fixture for second event
    )

    from datetime import UTC, datetime

    async with EspnFootballProvider(league=LEAGUE) as provider:
        summaries = await provider.list_upcoming_events(min_date=datetime(2026, 1, 1, tzinfo=UTC))

    assert len(summaries) >= 1
    first = summaries[0]
    assert isinstance(first, EventSummary)
    assert first.id == EVENT_ID or first.id == "401882918"
    assert "vs" not in first.name.lower()  # La Liga names are "Away at Home"


# --- Test 2: get_event_card devuelve 1 bout ----------------------------------


@respx.mock
async def test_get_event_card_one_bout() -> None:
    respx.get(url=_event_url()).respond(json=_load(f"event_{EVENT_ID}.json"))

    async with EspnFootballProvider(league=LEAGUE) as provider:
        event = await provider.get_event_card(EVENT_ID)

    assert isinstance(event, Event)
    assert event.id == EVENT_ID
    assert len(event.bouts) == 1
    bout = event.bouts[0]
    assert bout.match_number == 0  # football doesn't use matchNumber
    # 2 halves, 45 min each
    assert bout.format.regulation.periods == 2
    assert bout.format.regulation.clock == 2700.0
    # 2 competitors: home (red_corner, order=1 after remap) and away (blue_corner, order=2 after remap).
    # ESPN sends order 0 (home) and 1 (away); provider remaps 0->1, 1->2.
    red = bout.red_corner
    blue = bout.blue_corner
    assert red is not None
    assert blue is not None
    # Home team (order 0 in ESPN) -> red_corner (order 1 after remap)
    assert red.team is not None
    assert blue.team is not None


# --- Test 3: get_competition_status devuelve pre ------------------------------


@respx.mock
async def test_get_competition_status_pre() -> None:
    respx.get(url=_status_url()).respond(json=_load("competition_status_pre.json"))

    async with EspnFootballProvider(league=LEAGUE) as provider:
        status = await provider.get_competition_status(EVENT_ID, EVENT_ID)

    assert isinstance(status, CompetitionStatus)
    assert status.type.state == "pre"
    assert status.period == 0
    assert status.clock == 0.0


# --- Test 4: circuit breaker no abre en 4xx ----------------------------------


@respx.mock
async def test_circuit_breaker_does_not_open_on_4xx() -> None:
    respx.get(url=_events_list_url()).respond(status_code=404, json={"error": "not found"})

    async with EspnFootballProvider(
        league=LEAGUE,
        cb_fails=3,
        cb_open_seconds=60,
    ) as provider:
        with pytest.raises(httpx.HTTPStatusError):
            await provider._request(_events_list_url())
        assert provider.is_circuit_open is False


# --- Test 5: circuit breaker abre tras 5xx repetidos -------------------------


@respx.mock
async def test_circuit_breaker_opens_on_5xx() -> None:
    respx.get(url=_events_list_url()).respond(status_code=500, json={"error": "internal"})

    async with EspnFootballProvider(
        league=LEAGUE,
        cb_fails=2,
        cb_open_seconds=60,
    ) as provider:
        for _ in range(2):
            with contextlib.suppress(httpx.HTTPStatusError):
                await provider._request(_events_list_url())

        assert provider.is_circuit_open is True

        with pytest.raises(CircuitBreakerOpenError):
            await provider._request(_events_list_url())


# --- Test 6: get_team resuelve equipo de football ----------------------------


@respx.mock
async def test_get_team_resolves_name_and_logo() -> None:
    respx.get(url=_team_url(TEAM_HOME_ID)).respond(json=_load("team_96.json"))

    async with EspnFootballProvider(league=LEAGUE) as provider:
        team = await provider.get_team(TEAM_HOME_ID)

    assert isinstance(team, TeamDetail)
    assert team.display_name == "Alaves"
    assert team.logo_url is not None
    assert "96.png" in team.logo_url


# --- Test 7: get_team probing de years (404 en current, ok en +1) ------------


@respx.mock
async def test_get_team_year_probing_falls_back() -> None:
    """Si el equipo no se encuentra en el year actual, debe probar +1 y -1."""
    import datetime as dt

    year = dt.datetime.now(dt.UTC).year
    respx.get(url=_team_url_alt_year(TEAM_AWAY_ID, year)).respond(status_code=404)
    respx.get(url=_team_url_alt_year(TEAM_AWAY_ID, year + 1)).respond(json=_load("team_2922.json"))

    async with EspnFootballProvider(league=LEAGUE) as provider:
        team = await provider.get_team(TEAM_AWAY_ID)

    assert team.display_name == "Getafe"
    assert team.logo_url is not None


# --- Test 8: get_athlete lanza NotImplementedError ---------------------------


async def test_get_athlete_raises_not_implemented() -> None:
    async with EspnFootballProvider(league=LEAGUE) as provider:
        with pytest.raises(NotImplementedError):
            await provider.get_athlete("123")


# --- Test 9: dominio Bout.estimated_duration football ------------------------


def test_domain_bout_football_duration() -> None:
    from datetime import UTC, datetime

    from app.domain.entities import Bout

    b = Bout(
        id="test",
        match_number=1,
        date=datetime.now(UTC),
        sport="football",
    )
    # 2 halves * 2700s = 5400s (90 min)
    assert b.estimated_duration_seconds == 5400.0


# --- Test 10: dominio Card.previous_bout football (MVP: sin previo) -----------


def test_domain_card_football_no_previous() -> None:
    from datetime import UTC, datetime

    from app.domain.entities import Bout, Card

    b1 = Bout(id="b1", match_number=1, date=datetime.now(UTC), sport="football")
    card = Card(event_id="e1", event_name="Test", bouts=[b1], sport="football")
    assert card.previous_bout(b1) is None


# --- Test 11: BoutStatus.elapsed_seconds para football ------------------------


def test_bout_status_football_elapsed() -> None:
    from datetime import UTC, datetime

    from app.domain.entities import BoutStatus

    # 2nd half, clock=1200s (20 min into 2nd half). 45 min 1st half = 2700s.
    # elapsed = 2700 + 1200 = 3900
    bs = BoutStatus(
        bout_id="b1",
        state="in",
        clock=1200.0,
        period=2,
        sport="football",
        observed_at=datetime.now(UTC),
    )
    assert bs.elapsed_seconds == pytest.approx(3900.0)


def test_bout_status_football_elapsed_first_half() -> None:
    from datetime import UTC, datetime

    from app.domain.entities import BoutStatus

    # 1st half, clock=900s (15 min in). elapsed = 0 + 900 = 900
    bs = BoutStatus(
        bout_id="b1",
        state="in",
        clock=900.0,
        period=1,
        sport="football",
        observed_at=datetime.now(UTC),
    )
    assert bs.elapsed_seconds == pytest.approx(900.0)
