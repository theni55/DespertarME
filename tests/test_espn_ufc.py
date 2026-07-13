"""Tests del provider EspnUfcProvider con respx (mock httpx).

Cubre los 5 tests del checklist de Fase 0 (fases.md):
1. Listar eventos devuelve lista no vacía.
2. Detalle evento devuelve 14 combates con matchNumber ordenado y cardSegment.
3. Parser de status.type.state distingue pre/in/post.
4. Backoff retry en 429/5xx.
5. Circuit breaker abre tras N fallos consecutivos.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.providers import CircuitBreakerOpenError, EspnUfcProvider
from app.providers.models import Bout, CompetitionStatus, Event, EventSummary

BASE = "https://sports.core.api.espn.com/v2"
LEAGUE = "ufc"
FIX_DIR = Path(__file__).parent / "fixtures" / "espn_ufc"

EVENT_ID = "600059148"
COMP_ID = "401883599"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIX_DIR / name).read_text(encoding="utf-8"))


def _events_list_url() -> str:
    return f"{BASE}/sports/mma/leagues/{LEAGUE}/events?seasontype=2"


def _event_url(event_id: str = EVENT_ID) -> str:
    return f"{BASE}/sports/mma/leagues/{LEAGUE}/events/{event_id}"


def _status_url(event_id: str = EVENT_ID, comp_id: str = COMP_ID) -> str:
    return f"{BASE}/sports/mma/leagues/{LEAGUE}/events/{event_id}" f"/competitions/{comp_id}/status"


# --- Test 1: listar eventos devuelve lista no vacía ---------------------------


@respx.mock
async def test_list_upcoming_events_returns_non_empty_list() -> None:
    respx.get(url=_events_list_url()).respond(json=_load("event_list.json"))
    respx.get(url=_event_url()).respond(json=_load(f"event_{EVENT_ID}.json"))

    async with EspnUfcProvider() as provider:
        summaries = await provider.list_upcoming_events()

    assert len(summaries) >= 1
    summary = summaries[0]
    assert isinstance(summary, EventSummary)
    assert summary.id == EVENT_ID
    assert "UFC 329" in summary.name
    assert summary.date.startswith("2026-")


# --- Test 2: detalle evento devuelve 14 combates con matchNumber y cardSegment


@respx.mock
async def test_get_event_card_returns_14_bouts_ordered_with_card_segment() -> None:
    respx.get(url=_event_url()).respond(json=_load(f"event_{EVENT_ID}.json"))

    async with EspnUfcProvider() as provider:
        event = await provider.get_event_card(EVENT_ID)

    assert isinstance(event, Event)
    assert event.id == EVENT_ID
    assert event.name.startswith("UFC 329")
    assert len(event.bouts) == 14

    match_numbers = [b.match_number for b in event.bouts]
    assert match_numbers == sorted(match_numbers, reverse=True)
    assert match_numbers[0] == 14
    assert match_numbers[-1] == 1

    segments = {b.card_segment.name for b in event.bouts if b.card_segment}
    assert segments == {"main", "prelims1", "prelims2"}

    main_event = next(b for b in event.bouts if b.match_number == 1)
    assert isinstance(main_event, Bout)
    assert main_event.format is not None
    assert main_event.format.regulation.periods == 5


# --- Test 3: parser de status distingue pre/in/post ---------------------------


@pytest.mark.parametrize("state", ["pre", "in", "post"])
@respx.mock
async def test_get_competition_status_distinguishes_states(state: str) -> None:
    respx.get(url=_status_url()).respond(json=_load(f"competition_status_{state}.json"))

    async with EspnUfcProvider() as provider:
        status = await provider.get_competition_status(EVENT_ID, COMP_ID)

    assert isinstance(status, CompetitionStatus)
    assert status.type.state == state
    if state == "pre":
        assert not status.type.completed
        assert status.period == 0
    elif state == "in":
        assert not status.type.completed
        assert status.period == 2
        assert status.clock > 0
    else:
        assert status.type.completed
        assert status.period == 3


# --- Test 4: backoff retry en 429/5xx ----------------------------------------


@respx.mock
async def test_backoff_retries_on_429_then_succeeds() -> None:
    route = respx.get(url=_event_url())
    route.mock(
        side_effect=[
            httpx.Response(429, text="rate limited"),
            httpx.Response(200, json=_load(f"event_{EVENT_ID}.json")),
        ]
    )

    async with EspnUfcProvider(max_retries=3) as provider:
        event = await provider.get_event_card(EVENT_ID)

    assert event.id == EVENT_ID
    assert route.call_count == 2


@respx.mock
async def test_backoff_retries_on_5xx_then_succeeds() -> None:
    route = respx.get(url=_event_url())
    route.mock(
        side_effect=[
            httpx.Response(503, text="unavailable"),
            httpx.Response(200, json=_load(f"event_{EVENT_ID}.json")),
        ]
    )

    async with EspnUfcProvider(max_retries=3) as provider:
        event = await provider.get_event_card(EVENT_ID)

    assert event.id == EVENT_ID
    assert route.call_count == 2


@respx.mock
async def test_non_retryable_4xx_raises_without_retry() -> None:
    route = respx.get(url=_event_url())
    route.respond(status_code=404, text="not found")

    async with EspnUfcProvider(max_retries=3) as provider:
        with pytest.raises(httpx.HTTPStatusError):
            await provider.get_event_card(EVENT_ID)

    assert route.call_count == 1


# --- Test 5: circuit breaker abre tras N fallos consecutivos -----------------


@respx.mock
async def test_circuit_breaker_opens_after_consecutive_failures() -> None:
    route = respx.get(url=_event_url())
    route.respond(status_code=500, text="boom")

    async with EspnUfcProvider(
        max_retries=1, cb_fails=3, cb_open_seconds=60, clock=lambda: 0.0
    ) as provider:
        # 3 fallos consecutivos (sin retry porque max_retries=1)
        for _ in range(3):
            with pytest.raises(httpx.HTTPStatusError):
                await provider.get_event_card(EVENT_ID)

        assert provider.is_circuit_open
        assert route.call_count == 3

        # La 4ª llamada no toca la red: el CB lanza sin request
        with pytest.raises(CircuitBreakerOpenError):
            await provider.get_event_card(EVENT_ID)
        assert route.call_count == 3


@respx.mock
async def test_circuit_breaker_resets_on_success() -> None:
    route = respx.get(url=_event_url())
    route.mock(
        side_effect=[
            httpx.Response(500, text="boom"),
            httpx.Response(200, json=_load(f"event_{EVENT_ID}.json")),
            httpx.Response(500, text="boom"),
        ]
    )

    async with EspnUfcProvider(
        max_retries=1, cb_fails=3, cb_open_seconds=60, clock=lambda: 0.0
    ) as provider:
        # 1 fallo (no abre, cb_fails=3)
        with pytest.raises(httpx.HTTPStatusError):
            await provider.get_event_card(EVENT_ID)
        assert not provider.is_circuit_open

        # Éxito: reset del contador
        event = await provider.get_event_card(EVENT_ID)
        assert event.id == EVENT_ID
        assert not provider.is_circuit_open

        # 1 fallo de nuevo: no abre porque el contador se resetó
        with pytest.raises(httpx.HTTPStatusError):
            await provider.get_event_card(EVENT_ID)
        assert not provider.is_circuit_open


# --- get_athlete: nombre + headshot (MVP launch) ------------------------------


@respx.mock
async def test_get_athlete_returns_name_and_headshot() -> None:
    athlete_id = "4686725"
    respx.get(url=f"{BASE}/sports/mma/athletes/{athlete_id}").respond(
        json={
            "id": athlete_id,
            "displayName": "Cody Durden",
            "nickname": "Custom Made",
            "headshot": {
                "href": f"https://a.espncdn.com/i/headshots/mma/players/full/{athlete_id}.png",
                "alt": "Cody Durden",
            },
        }
    )

    async with EspnUfcProvider() as provider:
        athlete = await provider.get_athlete(athlete_id)

    assert athlete.display_name == "Cody Durden"
    assert athlete.headshot_url == (
        f"https://a.espncdn.com/i/headshots/mma/players/full/{athlete_id}.png"
    )


@respx.mock
async def test_get_athlete_headshot_fallback_when_missing() -> None:
    athlete_id = "111"
    respx.get(url=f"{BASE}/sports/mma/athletes/{athlete_id}").respond(
        json={"id": athlete_id, "displayName": "Sin Foto"}
    )

    async with EspnUfcProvider() as provider:
        athlete = await provider.get_athlete(athlete_id)

    # Fallback al patrón CDN estándar aunque ESPN no mande headshot.
    assert athlete.headshot_url == (
        f"https://a.espncdn.com/i/headshots/mma/players/full/{athlete_id}.png"
    )


def test_athlete_ref_parses_id_from_url() -> None:
    from app.providers.models import AthleteRef

    ref = AthleteRef.model_validate(
        {"$ref": "http://sports.core.api.espn.com/v2/sports/mma/athletes/4686725?lang=en"}
    )
    assert ref.athlete_id == "4686725"

    bad = AthleteRef.model_validate({"$ref": "http://example.com/nada"})
    assert bad.athlete_id is None
