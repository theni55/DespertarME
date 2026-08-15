"""Tests del dispatcher de buffers del scheduler (D57/D72/A9).

Verifica que cada deporte recibe el buffer correcto cuando el combate previo
termina (`in->post`), y que el estimador cae al buffer fijo MMA/Tenis cuando el
callback devuelve None.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.config import settings
from app.domain.entities import Bout
from app.scheduler import (
    _football_buffer_for,
    _nba_buffer_for,
    _nfl_buffer_for,
    _tennis_buffer_for,
)


def _bout(sport: str, match_number: int = 1) -> Bout:
    return Bout(
        id=f"{sport}-{match_number}",
        match_number=match_number,
        date=datetime(2026, 8, 15, tzinfo=UTC),
        periods=1,
        round_seconds=900.0,
        sport=sport,
    )


def test_tennis_buffer_uses_configured_900s() -> None:
    """A9 — tenis debe usar buffer_intermatch_tennis_seconds (900s), no el fijo MMA."""
    result = _tennis_buffer_for(_bout("tennis"))
    assert result == timedelta(seconds=settings.buffer_intermatch_tennis_seconds)


def test_tennis_buffer_none_for_other_sports() -> None:
    assert _tennis_buffer_for(_bout("mma")) is None
    assert _tennis_buffer_for(_bout("nba")) is None


def test_nba_buffer_quarter_and_halftime() -> None:
    assert _nba_buffer_for(_bout("nba", match_number=2)) == timedelta(
        seconds=settings.buffer_nba_quarter_seconds
    )
    assert _nba_buffer_for(_bout("nba", match_number=3)) == timedelta(
        seconds=settings.buffer_nba_halftime_seconds
    )
    assert _nba_buffer_for(_bout("tennis")) is None


def test_nfl_buffer_quarter_and_halftime() -> None:
    assert _nfl_buffer_for(_bout("nfl", match_number=2)) == timedelta(
        seconds=settings.buffer_nfl_quarter_seconds
    )
    assert _nfl_buffer_for(_bout("nfl", match_number=3)) == timedelta(
        seconds=settings.buffer_nfl_halftime_seconds
    )
    assert _nfl_buffer_for(_bout("mma")) is None


def test_football_buffer_returns_none_fixed_fallback() -> None:
    assert _football_buffer_for(_bout("football")) is None
    assert _football_buffer_for(_bout("mma")) is None
