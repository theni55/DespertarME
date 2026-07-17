"""Tests end-to-end del Poller (Fase 7a: device + FCM + bugs E2/E3/E6/E7).

Nueva semántica post-D40: el Poller ya NO dispara "llamar ahora". Mantiene la
estimación fresca en cada device mediante pushes `update`/`started`/`cancelled`.
El sonido lo reproduce la alarma local del dispositivo (Fase 7b).

Casos cubiertos:
- No hay push si la estimación no se mueve (>MIN_DELTA).
- Push `update` cuando el previo hace la transición in→post (E2).
- E2 — la estimación `post` se ancla a `observed_at`, no a `now`.
- E3 — target ya `in` → push `started` (no estimación fantasma).
- E3 — target ya `post` → push `cancelled` + marca sub como `fired`.
- E4 — el Poller deriva `previous_bout_id` de la card fresca (no persistido).
- E6 — UNIQUE `(device_id, bout_id)` + `fired_at_epoch_hour`.
- E7 — retries recortados (1 intento corto).
- E8 — caché de card por ciclo (no test directo, validado en integración).
- Idempotencia via Redis (try_mark_fired / get_last_estimate).
- Skip device sin fcm_token o inactivo.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from freezegun import freeze_time
from sqlalchemy import select

from app.db.models.alert_log import AlertLog
from app.db.models.devices import Device
from app.db.models.subscriptions import BoutSubscription
from app.engine.poller import MIN_DELTA_SECONDS, Poller
from app.engine.state import AlertState
from tests.conftest import FakeNotifier

# --- Helpers -----------------------------------------------------------------


async def _seed_device_and_sub(
    session,
    *,
    fcm_token: str | None = "tok-aaaa1111bbbb2222cccc",
    is_active: bool = True,
    lead_minutes: int = 15,
    bout_id: str = "comp-target",
) -> tuple[Device, BoutSubscription]:
    device = Device(
        id=f"dev-{uuid.uuid4().hex[:8]:08s}-bbbb-cccc-dddd-eeeeeeeeeeee",
        fcm_token=fcm_token,
        platform="android",
        timezone="Europe/Madrid",
        locale="es-ES",
        is_active=is_active,
    )
    session.add(device)
    await session.flush()
    sub = BoutSubscription(
        id=str(uuid.uuid4()),
        device_id=device.id,
        event_id="ev-1",
        bout_id=bout_id,
        target_match_number=1,
        lead_minutes=lead_minutes,
        status="active",
    )
    session.add(sub)
    await session.commit()
    return device, sub


# --- Tests base ------------------------------------------------------------


@freeze_time("2026-07-11T20:00:00+00:00")
async def test_poller_no_push_when_prev_pre(
    db_session, fake_provider, fake_redis
) -> None:
    """D45 — cuando el combate previo sigue en `pre`, no se dispara ningún push
    porque no hay información real de inicio (el backend espera a que el prev
    transicione a `in` o `post`)."""
    await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("pre")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert fired == 0
    assert len(notifier.pushes) == 0


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_pushes_update_when_prev_post(db_session, fake_provider, fake_redis) -> None:
    """E2: cuando el previo pasa a `post`, el Poller empuja `update` con la
    estimación = observed_at + buffer (300 s). observed_at = now tras primer poll."""
    await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    now = datetime.now(UTC)
    fired = await poller.poll_once(db_session, now=now)
    assert fired == 1
    assert notifier.pushes[0].message_type == "update"
    # estimado == now + 300 s (buffer D18: 5 min) dentro del rango
    assert notifier.pushes[0].estimated_start_at is not None
    val = int(notifier.pushes[0].estimated_start_at)
    pushed_start = datetime.fromtimestamp(val / 1000, tz=UTC)
    assert abs((pushed_start - (now + timedelta(seconds=300))).total_seconds()) < 1


@freeze_time("2026-07-11T21:40:00+00:00")
async def test_poller_e2_estimation_anchored_to_first_observation(
    db_session, fake_provider, fake_redis
) -> None:
    """E2 — si el previo sigue en `post` 14 min después, la estimación debe seguir
    anclada al primer `observed_at`, no deslizarse a `now + 300 s`."""
    _, sub = await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    # Primer poll a las 21:26. La estimación ancla = 21:26 + 300 s = 21:31.
    first_now = datetime(2026, 7, 11, 21, 26, tzinfo=UTC)
    await poller.poll_once(db_session, now=first_now)
    val_f = int(notifier.pushes[-1].estimated_start_at)
    first_est = datetime.fromtimestamp(val_f / 1000, tz=UTC)
    assert abs((first_est - (first_now + timedelta(seconds=300))).total_seconds()) < 1

    # Segundo poll 14 min después: estimación	anclada sigue siendo 21:31 (no 21:45).
    notifier.pushes.clear()
    # Forzamos un "movimiento" limpiando last_estimate para obligar a recalcular.
    await state.set_last_estimate(sub.id, sub.bout_id, first_est - timedelta(minutes=2))
    await poller.poll_once(db_session, now=datetime(2026, 7, 11, 21, 40, tzinfo=UTC))
    assert len(notifier.pushes) == 1
    val_s = int(notifier.pushes[-1].estimated_start_at)
    second_est = datetime.fromtimestamp(val_s / 1000, tz=UTC)
    # second_est sigue ≈ 21:31 (anclaje), NO 21:45 (now+300s)
    assert abs((second_est - first_est).total_seconds()) < 1
    assert abs((second_est - (first_now + timedelta(seconds=300))).total_seconds()) < 1


@freeze_time("2026-07-11T22:30:00+00:00")
async def test_poller_e3_pushes_started_when_target_in(
    db_session, fake_provider, fake_redis
) -> None:
    """E3 — si el combate objetivo ya está `in`, push `started` (no estimación fantasma)."""
    await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("in", clock=60.0, period=1)
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert fired == 1
    assert notifier.pushes[0].message_type == "started"


@freeze_time("2026-07-11T23:00:00+00:00")
async def test_poller_e3_pushes_cancelled_when_target_post_and_marks_fired(
    db_session, fake_provider, fake_redis
) -> None:
    """E3 — si el combate objetivo ya terminó sin que avisáramos, push `cancelled`
    y la suscripción se marca como `fired` (no se vuelve a procesar)."""
    _, sub = await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("post")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert fired == 1
    assert notifier.pushes[0].message_type == "cancelled"
    await db_session.refresh(sub)
    assert sub.status == "fired"


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_e3_idempotent_started_no_duplicate(
    db_session, fake_provider, fake_redis
) -> None:
    await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("in")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    f1 = await poller.poll_once(db_session, now=datetime.now(UTC))
    f2 = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert f1 == 1
    assert f2 == 0
    assert len(notifier.pushes) == 1


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_e4_derives_previous_bout_id_from_card_not_sub(
    db_session, fake_provider, fake_redis
) -> None:
    """E4 — `previous_bout_id` no se persiste; el Poller lo deriva de la card
    fresca (matchNumber+1). El FakeProvider devuelve `comp-prev` para match 2;
    target es match 1 → prev = match 2 = `comp-prev`."""
    _, sub = await _seed_device_and_sub(db_session)
    assert sub.previous_bout_id is None if hasattr(sub, "previous_bout_id") else True
    # BoutSubscription ya no tiene previous_bout_id: el campo se eliminó del modelo.
    assert not hasattr(sub, "previous_bout_id")
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    # Si no derivara el previo, get_competition_status devolvería el estado del
    # target (en este fake) y la estimación sería incoherente. Con E4, llama al
    # previo real (comp-prev matchNumber=2).
    await poller.poll_once(db_session, now=datetime.now(UTC))
    # Comprobamos que la transición del previo se persistió (signo de que sí
    # consultó prev.id == "comp-prev").
    got = await state.get_transition("ev-1", "comp-prev")
    assert got is not None


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_e7_retries_cut_short_on_failure(
    db_session, fake_provider, fake_redis
) -> None:
    """E7 — reintentos recortados a 1 corto. FakeNotifier falla 3 veces seguidas;
    el Poller debe hacer 2 intentos (1 + 1 retry) y registrar `failed`."""
    await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier(fail_count=3)
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=(0.0,))

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert fired == 0
    logs = (await db_session.execute(select(AlertLog))).scalars().all()
    assert len(logs) == 1
    assert logs[0].status == "failed"
    assert logs[0].attempts == 2  # 1 intento + 1 retry


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_e6_writes_epoch_hour_in_log(db_session, fake_provider, fake_redis) -> None:
    """E6 — `fired_at_epoch_hour` = epoch // 3600 (no now.hour)."""
    await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    now = datetime.now(UTC)
    await poller.poll_once(db_session, now=now)
    logs = (await db_session.execute(select(AlertLog))).scalars().all()
    assert logs[0].fired_at_epoch_hour == int(now.timestamp()) // 3600
    assert hasattr(logs[0], "fired_at_epoch_hour")
    assert not hasattr(logs[0], "fired_at_hour")  # renombrado


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_skips_device_without_fcm_token(db_session, fake_provider, fake_redis) -> None:
    """Sin fcm_token no hay push (equivalente a user sin teléfono en la era Twilio)."""
    await _seed_device_and_sub(db_session, fcm_token=None)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert fired == 0
    assert len(notifier.pushes) == 0


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_skips_inactive_device(db_session, fake_provider, fake_redis) -> None:
    await _seed_device_and_sub(db_session, is_active=False)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert fired == 0
    assert len(notifier.pushes) == 0


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_poller_payload_has_real_device_and_fighter_data(
    db_session, fake_provider, fake_redis
) -> None:
    """El payload del push lleva `device_id`, `fcm_token`, evento y fighters."""
    device, _ = await _seed_device_and_sub(db_session)
    fake_provider.set_prev_state("post")
    fake_provider.set_target_state("pre")
    state = AlertState(client=fake_redis)
    notifier = FakeNotifier()
    poller = Poller(provider=fake_provider, notifier=notifier, state=state, retry_delays=())

    fired = await poller.poll_once(db_session, now=datetime.now(UTC))
    assert fired == 1
    payload = notifier.pushes[0]
    assert payload.device_id == device.id
    assert payload.fcm_token == device.fcm_token
    assert payload.event_name == "UFC Test"
    assert "Conor Test" in (payload.fighters or "")
    assert "Max Fake" in (payload.fighters or "")
    assert payload.message_type in ("update", "started", "cancelled")


@freeze_time("2026-07-11T20:00:00+00:00")
async def test_alert_state_idempotency(fake_redis) -> None:
    state = AlertState(client=fake_redis, ttl_seconds=60)

    first = await state.try_mark_fired("sub-1", "bout-1", "post")
    second = await state.try_mark_fired("sub-1", "bout-1", "post")

    assert first is True
    assert second is False
    assert await state.was_fired("sub-1", "bout-1", "post") is True
    assert await state.was_fired("sub-1", "bout-1", "in") is False


@freeze_time("2026-07-11T21:26:00+00:00")
async def test_alert_state_remember_transition_anchors_first_observation(fake_redis) -> None:
    """E2 — `remember_transition` persistente: la primera observación gana."""
    state = AlertState(client=fake_redis)

    first = datetime(2026, 7, 11, 21, 25, tzinfo=UTC)
    second = datetime(2026, 7, 11, 21, 40, tzinfo=UTC)

    r1 = await state.remember_transition("ev-1", "comp-prev", first)
    r2 = await state.remember_transition("ev-1", "comp-prev", second)

    assert r1 == first  # primera observación gana
    assert r2 == first  # segunda no sobreescribe
    got = await state.get_transition("ev-1", "comp-prev")
    assert got == first


def test_min_delta_seconds_is_60() -> None:
    assert MIN_DELTA_SECONDS == 60
