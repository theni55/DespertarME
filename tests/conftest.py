from __future__ import annotations

from collections.abc import AsyncGenerator, Sequence

import pytest
import pytest_asyncio
from fakeredis import aioredis as fakeredis_aio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_session
from app.main import app
from app.providers.models import (
    AthleteDetail,
    AthleteHeadshot,
    AthleteRef,
    BoutFormat,
    BoutRegulation,
    CardSegment,
    CompetitionStatus,
    CompetitionStatusType,
    Competitor,
    Event,
    EventSummary,
    WeightClass,
)
from app.providers.models import (
    Bout as ProviderBout,
)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# --- BD en memoria (SQLite async) para tests de integración de API ----------


@pytest_asyncio.fixture
async def db_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def app_client(db_engine) -> AsyncGenerator[TestClient, None]:
    """Cliente de TestClient con la BD sobrescrita a SQLite en memoria."""
    maker = async_sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- Redis fake (fakeredis) -------------------------------------------------


@pytest_asyncio.fixture
async def fake_redis():
    client = fakeredis_aio.FakeRedis(decode_responses=True)
    yield client
    await client.aclose()


# --- Provider fake ----------------------------------------------------------


# Refs con formato real de ESPN para que `AthleteRef.athlete_id` parsee el id.
_ATHLETE_REF = "http://sports.core.api.espn.com/v2/sports/mma/athletes/{aid}?lang=en"

# Atletas fake conocidos por el FakeProvider (id -> nombre).
FAKE_ATHLETES = {
    "101": "Red Prev",
    "102": "Blue Prev",
    "201": "Conor Test",
    "202": "Max Fake",
}


class FakeProvider:
    """Provider que devuelve datos controlados sin red.

    Permite inyectar el estado del combate previo para simular transiciones
    pre → in → post en los tests del Poller.
    """

    def __init__(
        self,
        *,
        event_id: str = "ev-1",
        event_name: str = "UFC Test",
        prev_bout_id: str = "comp-prev",
        target_bout_id: str = "comp-target",
        prev_state: str = "pre",
        prev_clock: float = 0.0,
        prev_period: int = 0,
    ) -> None:
        self._event_id = event_id
        self._event_name = event_name
        self._prev_bout_id = prev_bout_id
        self._target_bout_id = target_bout_id
        self._prev_state = prev_state
        self._prev_clock = prev_clock
        self._prev_period = prev_period
        self.athlete_calls: list[str] = []

    def set_prev_state(self, state: str, clock: float = 0.0, period: int = 0) -> None:
        self._prev_state = state
        self._prev_clock = clock
        self._prev_period = period

    async def list_upcoming_events(self) -> Sequence[EventSummary]:
        return [EventSummary(id=self._event_id, name=self._event_name, date="2026-07-11T21:00Z")]

    async def get_event_card(self, event_id: str) -> Event:
        base = "2026-07-11T21:00Z"
        prev = ProviderBout(
            id=self._prev_bout_id,
            matchNumber=2,
            date=base,
            weight_class=WeightClass(text="Lightweight"),
            card_segment=CardSegment(name="main", description="Main Card"),
            format=BoutFormat(regulation=BoutRegulation(periods=3, clock=300.0)),
            competitors=[
                Competitor(
                    id="red-1",
                    order=1,
                    athlete=AthleteRef.model_validate({"$ref": _ATHLETE_REF.format(aid="101")}),
                ),
                Competitor(
                    id="blue-1",
                    order=2,
                    athlete=AthleteRef.model_validate({"$ref": _ATHLETE_REF.format(aid="102")}),
                ),
            ],
        )
        target = ProviderBout(
            id=self._target_bout_id,
            matchNumber=1,
            date="2026-07-11T21:30Z",
            weight_class=WeightClass(text="Welterweight"),
            card_segment=CardSegment(name="main", description="Main Card"),
            format=BoutFormat(regulation=BoutRegulation(periods=5, clock=300.0)),
            competitors=[
                Competitor(
                    id="red-2",
                    order=1,
                    athlete=AthleteRef.model_validate({"$ref": _ATHLETE_REF.format(aid="201")}),
                ),
                Competitor(
                    id="blue-2",
                    order=2,
                    athlete=AthleteRef.model_validate({"$ref": _ATHLETE_REF.format(aid="202")}),
                ),
            ],
        )
        return Event(
            id=self._event_id,
            name=self._event_name,
            date=base,
            competitions=[prev, target],
        )

    async def get_competition_status(self, event_id: str, competition_id: str) -> CompetitionStatus:
        return CompetitionStatus(
            clock=self._prev_clock,
            period=self._prev_period,
            type=CompetitionStatusType(
                state=self._prev_state,  # type: ignore[arg-type]
                completed=(self._prev_state == "post"),
            ),
        )

    async def get_athlete(self, athlete_id: str) -> AthleteDetail:
        self.athlete_calls.append(athlete_id)
        name = FAKE_ATHLETES.get(athlete_id, f"Fighter {athlete_id}")
        return AthleteDetail(
            id=athlete_id,
            displayName=name,
            headshot=AthleteHeadshot(
                href=f"https://a.espncdn.com/i/headshots/mma/players/full/{athlete_id}.png"
            ),
        )


@pytest.fixture
def fake_provider() -> FakeProvider:
    return FakeProvider()
