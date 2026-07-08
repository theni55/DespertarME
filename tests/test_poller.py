"""Tests end-to-end del Poller (Fase 2b).

Simula transiciones de estado del combate previo (pre → in → post) y verifica:
- La alerta no se dispara cuando falta tiempo.
- La alerta se dispara cuando el previo termina y start-now <= lead_minutes.
- Idempotencia: no se dispara dos veces para el mismo estado.
- Reintentos: si el notifier falla, reintenta y luego marca failed.
- Se registra en alert_log (BD).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from freezegun import freeze_time
from sqlalchemy import select

from app.db.models.alert_log import AlertLog
from app.db.models.subscriptions import BoutSubscription
from app.db.models.users import User
from app.engine.poller import Poller
from app.engine.state import AlertState
from app.notifiers.dummy import DummyNotifier

# --- Helpers -----------------------------------------------------------------


async def _seed_user_and_sub(
    session,
    *,
    prev_state: str = "pre",
    lead_minutes: int = 15,
) -> tuple[User, BoutSubscription]:
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        hashed_password="x",
        phone_normalized="+34600000000",
    )
    session.add(user)
    await session.flush()

    sub = BoutSubscription(
        id=str(uuid.uuid4()),
        user_id=user.id,
        event_id="ev-1",
        bout_id="comp-target",
        target_match_number=1,
        previous_bout_id="comp-prev",
        previous_match_number=2,
        lead_minutes=lead_minutes,
        status="active",
    )
    session.add(sub)
    await session.commit()
    return user, sub


# --- Tests -------------------------------------------------------------------


@freeze_time("2026-07-11T20:00:00+00:00")
async def test_poller_does_not_fire_when_far_from_start(
    db_session, fake_provider, fake_redis
) -> None:
    await _seed_user_and_sub(db_session)
    state = AlertState(client=fake_redis)
    poller = Poller(
        provider=fake_provider,
        notifier=DummyNotifier(),
        state=state,
        retry_delays=(),
    )

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))

    assert fired == 0
    logs = (await db_session.execute(select(AlertLog))).scalars().all()
    assert len(logs) == 0


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_fires_when_prev_post_and_within_lead(
    db_session, fake_provider, fake_redis
) -> None:
    user, sub = await _seed_user_and_sub(db_session)
    fake_provider.set_prev_state("post")
    state = AlertState(client=fake_redis)
    notifier = DummyNotifier()
    poller = Poller(
        provider=fake_provider,
        notifier=notifier,
        state=state,
        retry_delays=(),
    )

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))

    assert fired == 1
    await db_session.refresh(sub)
    assert sub.status == "fired"

    logs = (await db_session.execute(select(AlertLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "fired"
    assert logs[0].user_id == user.id


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_idempotent_no_duplicate_for_same_state(
    db_session, fake_provider, fake_redis
) -> None:
    await _seed_user_and_sub(db_session)
    fake_provider.set_prev_state("post")
    state = AlertState(client=fake_redis)
    poller = Poller(
        provider=fake_provider,
        notifier=DummyNotifier(),
        state=state,
        retry_delays=(),
    )

    fired1 = await poller.poll_once(db_session, now=datetime.now(UTC))
    fired2 = await poller.poll_once(db_session, now=datetime.now(UTC))

    assert fired1 == 1
    assert fired2 == 0
    logs = (await db_session.execute(select(AlertLog))).scalars().all()
    assert len(logs) == 1


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_retries_on_notifier_failure(db_session, fake_provider, fake_redis) -> None:
    await _seed_user_and_sub(db_session)
    fake_provider.set_prev_state("post")
    state = AlertState(client=fake_redis)
    notifier = DummyNotifier(fail_on_phone="+000000000")
    poller = Poller(
        provider=fake_provider,
        notifier=notifier,
        state=state,
        retry_delays=(0.0, 0.0, 0.0),
    )

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))

    assert fired == 0
    logs = (await db_session.execute(select(AlertLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].attempts == 4


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_fires_on_prev_in_close_to_end(db_session, fake_provider, fake_redis) -> None:
    await _seed_user_and_sub(db_session, lead_minutes=20)
    fake_provider.set_prev_state("in", clock=60.0, period=3)
    state = AlertState(client=fake_redis)
    poller = Poller(
        provider=fake_provider,
        notifier=DummyNotifier(),
        state=state,
        retry_delays=(),
    )

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))

    assert fired == 1


@freeze_time("2026-07-11T20:00:00+00:00")
async def test_alert_state_idempotency(fake_redis) -> None:
    state = AlertState(client=fake_redis, ttl_seconds=60)

    first = await state.try_mark_fired("sub-1", "bout-1", "post")
    second = await state.try_mark_fired("sub-1", "bout-1", "post")

    assert first is True
    assert second is False
    assert await state.was_fired("sub-1", "bout-1", "post") is True
    assert await state.was_fired("sub-1", "bout-1", "in") is False
