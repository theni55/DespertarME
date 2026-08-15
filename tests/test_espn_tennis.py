"""Tests del provider EspnTennisProvider.

Cubre los escenarios de esquina del filtro universal de visibilidad (D78):
- Torneos singles/dobles separados correctamente.
- Dobles con todos los bouts TBD/Bye no generan entrada _doubles.
- Dobles con todos los bouts acabados (winner=true) no generan entrada _doubles.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
import respx

from app.providers.espn_tennis import EspnTennisProvider

BASE = "https://sports.core.api.espn.com/v2"
LEAGUE = "atp"
FIX_DIR = Path(__file__).parent / "fixtures" / "espn_tennis"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIX_DIR / name).read_text(encoding="utf-8"))


# ----------------------------------------------------------- fixtures sinteticos


def _make_tournament(tournament_id: str, name: str, competitions: list[dict]) -> dict:
    # Fecha dinamica (futuro cercano) para no depender del reloj: el provider
    # filtra torneos fuera de la ventana de 14 dias, y una fecha fija acabaria
    # en el pasado con el tiempo (mismo bug que el test NFL de A18).
    future = (datetime.now(UTC) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%MZ")
    return {
        "id": tournament_id,
        "name": name,
        "date": future,
        "status": {"type": {"state": "in", "completed": False}},
        "competitions": competitions,
    }


def _make_comp(
    comp_type: str,
    red_name: str,
    red_id: str,
    blue_name: str,
    blue_id: str,
    winner: str | None = None,
) -> dict:
    red = {"name": red_name, "id": red_id, "order": 1}
    blue = {"name": blue_name, "id": blue_id, "order": 2}
    if winner == "red":
        red["winner"] = True
    elif winner == "blue":
        blue["winner"] = True
    return {
        "type": {"text": comp_type},
        "competitors": [red, blue],
    }


# --------------------------------------------------------------------- helpers


def _events_list_url() -> str:
    return f"{BASE}/sports/tennis/leagues/{LEAGUE}/events?seasontype=2"


def _event_url(event_id: str) -> str:
    return f"{BASE}/sports/tennis/leagues/{LEAGUE}/events/{event_id}"


# ---------------------------------------------------------------------- tests


class TestListUpcomingEventsDoublesFilter:
    @pytest.mark.asyncio
    async def test_doubles_entry_not_created_when_all_bye_tbd(self):
        """Si todos los partidos de dobles son Bye/TBD, no crear _doubles."""
        tournament = _make_tournament(
            "999-2026",
            "Test Open",
            [
                _make_comp("Men's Singles", "Djokovic", "1", "Nadal", "2"),
                _make_comp("Men's Doubles", "Bye", "0", "TBD", "2147483647"),
                _make_comp("Men's Doubles", "TBD", "2147483647", "Bye", "0"),
            ],
        )

        provider = EspnTennisProvider(league="atp")
        with respx.mock(base_url=BASE) as mock:
            mock.get(_events_list_url()).respond(
                json={"items": [{"$ref": f"{BASE}/sports/tennis/leagues/{LEAGUE}/events/999-2026"}]}
            )
            mock.get(_event_url("999-2026")).respond(json=tournament)

            events = await provider.list_upcoming_events()

        ids = [e.id for e in events]
        assert (
            "999-2026_doubles" not in ids
        ), "no deberia crear entrada _doubles cuando todos son Bye/TBD"
        assert "999-2026" in ids, "la entrada de singles debe existir"

    @pytest.mark.asyncio
    async def test_doubles_entry_not_created_when_all_finished(self):
        """Si todos los partidos de dobles ya acabaron (winner=true), no crear _doubles."""
        tournament = _make_tournament(
            "998-2026",
            "Finished Open",
            [
                _make_comp("Men's Singles", "Alcaraz", "10", "Sinner", "20"),
                _make_comp("Men's Doubles", "Bryans", "100", "Woodies", "200", winner="red"),
                _make_comp("Men's Doubles", "Nestors", "300", "Zimonjics", "400", winner="blue"),
            ],
        )

        provider = EspnTennisProvider(league="atp")
        with respx.mock(base_url=BASE) as mock:
            mock.get(_events_list_url()).respond(
                json={"items": [{"$ref": f"{BASE}/sports/tennis/leagues/{LEAGUE}/events/998-2026"}]}
            )
            mock.get(_event_url("998-2026")).respond(json=tournament)

            events = await provider.list_upcoming_events()

        ids = [e.id for e in events]
        assert (
            "998-2026_doubles" not in ids
        ), "no deberia crear entrada _doubles cuando todos estan acabados"
        assert "998-2026" in ids

    @pytest.mark.asyncio
    async def test_doubles_entry_created_when_some_alive(self):
        """Si AL MENOS un partido de dobles esta vivo (sin winner + nombres reales), crear _doubles."""
        tournament = _make_tournament(
            "997-2026",
            "Mixed Open",
            [
                _make_comp("Men's Singles", "Federer", "5", "Murray", "6"),
                _make_comp("Men's Doubles", "Smith", "50", "Jones", "60", winner="red"),
                _make_comp("Men's Doubles", "Chang", "70", "Ivanisevic", "80"),  # vivo
            ],
        )

        provider = EspnTennisProvider(league="atp")
        with respx.mock(base_url=BASE) as mock:
            mock.get(_events_list_url()).respond(
                json={"items": [{"$ref": f"{BASE}/sports/tennis/leagues/{LEAGUE}/events/997-2026"}]}
            )
            mock.get(_event_url("997-2026")).respond(json=tournament)

            events = await provider.list_upcoming_events()

        ids = [e.id for e in events]
        assert (
            "997-2026_doubles" in ids
        ), "deberia crear entrada _doubles porque hay al menos un partido vivo"
        assert "997-2026" in ids
