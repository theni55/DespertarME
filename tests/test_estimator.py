"""Tests del EstimatorEngine (Fase 2a).

Tests aislados con freezegun (reloj fake) y dataclasses del dominio.
Sin Redis, sin BD, sin provider real.

Escenarios cubiertos:
- prev_status None → fecha programada (confidence low).
- prev_state pre → fecha programada (confidence low).
- prev_state in → start = now + (duración_media − ya_transcurrido) + buffer.
- prev_state post → start = now + buffer (D18: 5 min, confidence high).
- should_fire dispara cuando start_at - now <= lead_seconds.
- cadencia de polling adaptativa (D15): 60/10/5 s.
- duración media estimada para 3 y 5 rounds.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time

from app.domain.entities import Athlete, Bout, BoutStatus, Card, EstimatedStart
from app.engine.estimator import EstimatorConfig, EstimatorEngine

# --- Fixtures de dominio -----------------------------------------------------


def make_card() -> Card:
    """Tarjeta con 2 combates: #1 (main event, 5 rounds) y #2 (previo, 3 rounds)."""
    base = datetime(2026, 7, 11, 21, 0, tzinfo=UTC)
    prev = Bout(
        id="comp-2",
        match_number=2,
        date=base,
        card_segment="main",
        weight_class="Lightweight",
        periods=3,
        red=Athlete(id="red-1"),
        blue=Athlete(id="blue-1"),
    )
    target = Bout(
        id="comp-1",
        match_number=1,
        date=base + timedelta(minutes=30),
        card_segment="main",
        weight_class="Welterweight",
        periods=5,
        red=Athlete(id="red-2"),
        blue=Athlete(id="blue-2"),
    )
    return Card(event_id="ev-1", event_name="UFC Test", bouts=[prev, target])


def make_target(card: Card) -> Bout:
    b = card.bout_by_match_number(1)
    assert b is not None
    return b


def make_prev_bout(card: Card) -> Bout:
    b = card.bout_by_match_number(2)
    assert b is not None
    return b


# --- Tests de estimación -----------------------------------------------------


def test_estimate_no_prev_status_uses_scheduled_date() -> None:
    card = make_card()
    target = make_target(card)
    now = datetime(2026, 7, 11, 20, 0, tzinfo=UTC)
    engine = EstimatorEngine()

    est = engine.estimate(card, target, prev_status=None, now=now)

    assert est.bout_id == target.id
    assert est.start_at == target.date
    assert est.confidence == "low"
    assert "sin datos" in est.reason


def test_estimate_prev_pre_uses_scheduled_date() -> None:
    card = make_card()
    target = make_target(card)
    prev = make_prev_bout(card)
    now = datetime(2026, 7, 11, 20, 50, tzinfo=UTC)
    engine = EstimatorEngine()

    est = engine.estimate(
        card,
        target,
        prev_status=BoutStatus(bout_id=prev.id, state="pre"),
        now=now,
    )

    assert est.start_at == target.date
    assert est.confidence == "low"


def test_estimate_prev_in_recalculates_with_remaining_time() -> None:
    card = make_card()
    target = make_target(card)
    prev = make_prev_bout(card)
    # prev_duration = 3*300 + 2*60 = 1020 s (17 min)
    # elapsed = 2*300 - 60 = 540 s (9 min) → remaining = 480 s (8 min)
    # start = now + 480 + 300 = now + 780 s (13 min)
    now = datetime(2026, 7, 11, 20, 55, tzinfo=UTC)
    engine = EstimatorEngine()

    est = engine.estimate(
        card,
        target,
        prev_status=BoutStatus(bout_id=prev.id, state="in", clock=60.0, period=2),
        now=now,
    )

    expected = now + timedelta(seconds=480 + 300)
    assert est.start_at == expected
    assert est.confidence == "medium"
    assert "en curso" in est.reason


def test_estimate_prev_post_uses_now_plus_buffer() -> None:
    card = make_card()
    target = make_target(card)
    prev = make_prev_bout(card)
    now = datetime(2026, 7, 11, 21, 5, tzinfo=UTC)
    engine = EstimatorEngine()

    est = engine.estimate(
        card,
        target,
        prev_status=BoutStatus(bout_id=prev.id, state="post", completed=True),
        now=now,
    )

    expected = now + timedelta(seconds=300)
    assert est.start_at == expected
    assert est.confidence == "high"
    assert "D18" in est.reason


def test_estimate_no_previous_bout_in_card() -> None:
    """Si el target es el primer combate (matchNumber más alto), no hay previo."""
    single = Bout(id="only", match_number=5, date=datetime(2026, 7, 11, 21, tzinfo=UTC))
    card = Card(event_id="ev", event_name="Test", bouts=[single])
    now = datetime(2026, 7, 11, 20, tzinfo=UTC)
    engine = EstimatorEngine()

    est = engine.estimate(card, single, prev_status=None, now=now)

    assert est.start_at == single.date
    assert est.confidence == "medium"


# --- Tests de should_fire ----------------------------------------------------


def test_should_fire_when_within_lead() -> None:
    now = datetime(2026, 7, 11, 20, 50, tzinfo=UTC)
    est_start = EstimatedStart(bout_id="x", start_at=now + timedelta(minutes=10))
    assert est_start.should_fire(now, lead_seconds=15 * 60)
    assert not est_start.should_fire(now, lead_seconds=5 * 60)


def test_should_fire_when_exactly_at_lead_boundary() -> None:
    now = datetime(2026, 7, 11, 20, 50, tzinfo=UTC)
    est_start = EstimatedStart(bout_id="x", start_at=now + timedelta(minutes=15))
    assert est_start.should_fire(now, lead_seconds=15 * 60)


# --- Tests de cadencia de polling (D15) --------------------------------------


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (None, 60),
        ("pre", 60),
        ("in", 10),
        ("post", 5),
    ],
)
def test_poll_interval_adaptive(state: str | None, expected: int) -> None:
    engine = EstimatorEngine()
    assert engine.poll_interval(state) == expected


def test_poll_interval_uses_config() -> None:
    cfg = EstimatorConfig(
        poll_default_seconds=30, poll_prev_in_advanced_seconds=7, poll_prev_post_seconds=3
    )
    engine = EstimatorEngine(cfg)
    assert engine.poll_interval(None) == 30
    assert engine.poll_interval("pre") == 30
    assert engine.poll_interval("in") == 7
    assert engine.poll_interval("post") == 3


# --- Tests de duración media estimada ----------------------------------------


def test_estimated_duration_3_rounds() -> None:
    b = Bout(id="x", match_number=2, date=datetime(2026, 1, 1, tzinfo=UTC), periods=3)
    # 3*300 + 2*60 = 1020
    assert b.estimated_duration_seconds == 1020


def test_estimated_duration_5_rounds() -> None:
    b = Bout(id="x", match_number=1, date=datetime(2026, 1, 1, tzinfo=UTC), periods=5)
    # 5*300 + 4*60 = 1740
    assert b.estimated_duration_seconds == 1740


# --- Test end-to-end con freezegun: transición pre → in → post ----------------


@freeze_time("2026-07-11T20:50:00+00:00")
def test_full_transition_pre_to_in_to_post() -> None:
    card = make_card()
    target = make_target(card)
    prev = make_prev_bout(card)
    engine = EstimatorEngine()

    # Estado 1: previo en pre → fecha programada
    est1 = engine.estimate(card, target, BoutStatus(prev.id, "pre"), now=datetime.now(UTC))
    assert est1.start_at == target.date

    # Estado 2: previo en in (round 2, 2:00 restante) → recálculo
    est2 = engine.estimate(
        card,
        target,
        BoutStatus(prev.id, "in", clock=120.0, period=2),
        now=datetime.now(UTC),
    )
    assert est2.start_at > datetime.now(UTC)

    # Estado 3: previo en post → now + buffer
    est3 = engine.estimate(
        card,
        target,
        BoutStatus(prev.id, "post", completed=True),
        now=datetime.now(UTC),
    )
    assert est3.start_at == datetime.now(UTC) + timedelta(seconds=300)
    assert est3.confidence == "high"
