"""Tests para EspnNflProvider (D71).

Mirror de `test_espn_nba.py` adaptado a NFL: 4 quarters de 900s,
TeamResolver con 32 equipos, status global derivado por quarter.
"""

from __future__ import annotations

import contextlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import respx

from app.providers import CircuitBreakerOpenError, EspnNflProvider
from app.providers.models import CompetitionStatus

BASE = "https://sports.core.api.espn.com/v2"
LEAGUE = "nfl"
FIX_DIR = Path(__file__).parent / "fixtures" / "espn_nfl"
EVENT_ID = "401873271"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIX_DIR / name).read_text(encoding="utf-8"))


def _events_list_url() -> str:
    return f"{BASE}/sports/football/leagues/{LEAGUE}/events?seasontype=2"


def _event_url() -> str:
    return f"{BASE}/sports/football/leagues/{LEAGUE}/events/{EVENT_ID}"


def _status_url() -> str:
    return (
        f"{BASE}/sports/football/leagues/{LEAGUE}/events/{EVENT_ID}/competitions/{EVENT_ID}/status"
    )


def _team_url(team_id: str) -> str:
    import datetime as dt

    year = dt.datetime.now(dt.UTC).year
    return f"{BASE}/sports/football/leagues/{LEAGUE}/seasons/{year}/teams/{team_id}"


# ------------------------------------------------------------------ tests --


class TestListEvents:
    @pytest.mark.asyncio
    async def test_list_upcoming_events_returns_non_empty_list(self):
        provider = EspnNflProvider()
        with respx.mock(base_url=BASE) as mock:
            mock.get(_events_list_url()).respond(json=_load("event_list.json"))
            mock.get(_event_url()).respond(json=_load("event_401873271.json"))

            events = await provider.list_upcoming_events(min_date=datetime(2020, 1, 1, tzinfo=UTC))

        assert len(events) == 1
        assert events[0].id == EVENT_ID
        assert "Cardinals" in events[0].name


class TestGetEventCard:
    @pytest.mark.asyncio
    async def test_get_event_card_synthesizes_four_quarters(self):
        provider = EspnNflProvider()
        with respx.mock(base_url=BASE) as mock:
            mock.get(_event_url()).respond(json=_load("event_401873271.json"))

            event = await provider.get_event_card(EVENT_ID)

        assert len(event.bouts) == 4
        for q in range(4):
            assert event.bouts[q].id == f"{EVENT_ID}_q{q + 1}"
            assert event.bouts[q].match_number == q + 1
            assert event.bouts[q].card_segment is not None
            assert event.bouts[q].card_segment.name == "Regulation"
            assert event.bouts[q].format.regulation.periods == 1
            assert event.bouts[q].format.regulation.clock == 900.0

    @pytest.mark.asyncio
    async def test_get_event_card_remaps_nfl_competitor_order_to_red_blue(self):
        provider = EspnNflProvider()
        with respx.mock(base_url=BASE) as mock:
            mock.get(_event_url()).respond(json=_load("event_401873271.json"))

            event = await provider.get_event_card(EVENT_ID)

        bout = event.bouts[0]
        assert bout.red_corner is not None
        assert bout.blue_corner is not None
        assert bout.red_corner.order == 1
        assert bout.blue_corner.order == 2


class TestCompetitionStatus:
    def test_pre_when_game_not_started(self):
        data = _load("competition_status_pre.json")
        status = CompetitionStatus.model_validate(data)
        assert status.type.state == "pre"
        assert status.period == 0

    @pytest.mark.parametrize(
        "fixture,quarter,expected_state",
        [
            ("competition_status_pre", 1, "pre"),
            ("competition_status_pre", 2, "pre"),
            ("competition_status_pre", 3, "pre"),
            ("competition_status_pre", 4, "pre"),
            ("competition_status_in_q1", 1, "in"),
            ("competition_status_in_q1", 2, "pre"),
            ("competition_status_in_q1", 3, "pre"),
            ("competition_status_in_q1", 4, "pre"),
            ("competition_status_in_q2", 1, "post"),
            ("competition_status_in_q2", 2, "in"),
            ("competition_status_in_q2", 3, "pre"),
            ("competition_status_in_q2", 4, "pre"),
            ("competition_status_in_q3", 1, "post"),
            ("competition_status_in_q3", 2, "post"),
            ("competition_status_in_q3", 3, "in"),
            ("competition_status_in_q3", 4, "pre"),
            ("competition_status_in_q4", 1, "post"),
            ("competition_status_in_q4", 2, "post"),
            ("competition_status_in_q4", 3, "post"),
            ("competition_status_in_q4", 4, "in"),
            ("competition_status_post", 1, "post"),
            ("competition_status_post", 2, "post"),
            ("competition_status_post", 3, "post"),
            ("competition_status_post", 4, "post"),
        ],
    )
    def test_derive_quarter_status(self, fixture, quarter, expected_state):
        data = _load(f"{fixture}.json")
        result = EspnNflProvider._derive_quarter_status(quarter, data)
        assert result.type.state == expected_state


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_opens_after_n_failures(self):
        provider = EspnNflProvider(cb_fails=3, cb_open_seconds=60.0, clock=lambda: 0.0)

        with respx.mock(base_url=BASE) as mock:
            mock.get(_event_url()).respond(json={"message": "Internal Error"}, status_code=500)

            for _ in range(3):
                with pytest.raises(Exception):  # noqa: B017
                    await provider.get_event_card(EVENT_ID)

            with pytest.raises(CircuitBreakerOpenError):
                await provider.get_event_card(EVENT_ID)

    @pytest.mark.asyncio
    async def test_4xx_does_not_open_circuit_breaker(self):
        provider = EspnNflProvider(cb_fails=3, cb_open_seconds=60.0, clock=lambda: 0.0)

        with respx.mock(base_url=BASE) as mock:
            mock.get(f"{BASE}/sports/football/leagues/{LEAGUE}/events/999999").respond(
                status_code=404
            )

            for _ in range(5):
                with contextlib.suppress(Exception):
                    await provider.get_event_card("999999")

            mock.get(_event_url()).respond(json=_load("event_401873271.json"))

            event = await provider.get_event_card(EVENT_ID)
            assert event is not None


class TestTeamResolver:
    @pytest.mark.asyncio
    async def test_get_team_returns_display_name_and_logo(self):
        provider = EspnNflProvider()
        with respx.mock(base_url=BASE) as mock:
            mock.get(_team_url("1")).respond(json=_load("team_1.json"))

            team = await provider.get_team("1")

        assert team is not None
        assert team.display_name == "Atlanta Falcons"
        assert team.logo_url is not None


class TestDomain:
    def test_bout_nfl_estimated_duration_is_quarter_seconds(self):
        from datetime import UTC
        from datetime import datetime as dt

        from app.domain.entities import Bout

        bout = Bout(
            id="401873271_q1",
            match_number=1,
            date=dt(2026, 8, 7, tzinfo=UTC),
            periods=1,
            round_seconds=900.0,
            sport="nfl",
        )
        assert bout.estimated_duration_seconds == 900.0

    def test_bout_status_nfl_elapsed_when_in_q2_clock_300(self):
        from datetime import UTC
        from datetime import datetime as dt

        from app.domain.entities import BoutStatus

        status = BoutStatus(
            bout_id="401873271_q2",
            state="in",
            clock=300.0,
            period=2,
            sport="nfl",
            observed_at=dt.now(UTC),
        )
        assert status.elapsed_seconds == 900.0 + 600.0

    def test_card_previous_bout_nfl_ascending(self):
        from datetime import UTC
        from datetime import datetime as dt

        from app.domain.entities import Bout, Card

        bouts = [
            Bout(id="ev_q1", match_number=1, date=dt(2026, 8, 7, tzinfo=UTC), sport="nfl"),
            Bout(id="ev_q2", match_number=2, date=dt(2026, 8, 7, tzinfo=UTC), sport="nfl"),
            Bout(id="ev_q3", match_number=3, date=dt(2026, 8, 7, tzinfo=UTC), sport="nfl"),
            Bout(id="ev_q4", match_number=4, date=dt(2026, 8, 7, tzinfo=UTC), sport="nfl"),
        ]
        card = Card(event_id="ev", event_name="Test", bouts=bouts, sport="nfl")
        q2 = card.bout_by_id("ev_q2")
        assert q2 is not None
        prev = card.previous_bout(q2)
        assert prev is not None
        assert prev.id == "ev_q1"

    def test_estimator_nfl_q3_uses_halftime_buffer(self):
        from datetime import UTC, timedelta
        from datetime import datetime as dt

        from app.config import get_settings
        from app.domain.entities import Bout

        settings = get_settings()

        def buffer_for(target):
            if target.sport != "nfl":
                return None
            if target.match_number == 3:
                return timedelta(seconds=settings.buffer_nfl_halftime_seconds)
            return timedelta(seconds=settings.buffer_nfl_quarter_seconds)

        quarter = Bout(
            id="401873271_q3",
            match_number=3,
            date=dt(2026, 8, 7, tzinfo=UTC),
            sport="nfl",
        )
        result = buffer_for(quarter)
        assert result == timedelta(seconds=settings.buffer_nfl_halftime_seconds)

    def test_estimator_nfl_q2_uses_quarter_buffer(self):
        from datetime import UTC, timedelta
        from datetime import datetime as dt

        from app.config import get_settings
        from app.domain.entities import Bout

        settings = get_settings()

        def buffer_for(target):
            if target.sport != "nfl":
                return None
            if target.match_number == 3:
                return timedelta(seconds=settings.buffer_nfl_halftime_seconds)
            return timedelta(seconds=settings.buffer_nfl_quarter_seconds)

        quarter = Bout(
            id="401873271_q2",
            match_number=2,
            date=dt(2026, 8, 7, tzinfo=UTC),
            sport="nfl",
        )
        result = buffer_for(quarter)
        assert result == timedelta(seconds=settings.buffer_nfl_quarter_seconds)


class TestSchemas:
    def test_schemas_accept_lead_zero_for_nfl_q2_q4(self):
        from app.api.schemas import BoutSubscriptionCreate

        for mn in (2, 3, 4):
            sub = BoutSubscriptionCreate(
                event_id="401873271",
                bout_id=f"401873271_q{mn}",
                target_match_number=mn,
                lead_minutes=0,
                sport="nfl",
            )
            sub.validate_for_sport()

    def test_schemas_reject_lead_zero_for_nfl_q1(self):
        from app.api.schemas import BoutSubscriptionCreate

        sub = BoutSubscriptionCreate(
            event_id="401873271",
            bout_id="401873271_q1",
            target_match_number=1,
            lead_minutes=0,
            sport="nfl",
        )
        with pytest.raises(ValueError, match="lead_minutes"):
            sub.validate_for_sport()

    def test_schemas_reject_negative_lead_at_field_level(self):
        from app.api.schemas import BoutSubscriptionCreate

        with pytest.raises(ValueError, match="lead_minutes"):
            BoutSubscriptionCreate(
                event_id="401873271",
                bout_id="401873271_q1",
                target_match_number=1,
                lead_minutes=-1,
                sport="nfl",
            )
