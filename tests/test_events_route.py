"""Tests del router /api/events (Fase 7a) con EspnUfcProvider mockeado vía respx.

Verifica:
- `GET /api/events` devuelve la lista con `image_url=None` (D42: ESPN no sirve
  imágenes de evento; la app usa `hero.webp` estática).
- `GET /api/events/{id}` devuelve la tarjeta con bouts ordenados y
  `previous_bout_id` calculado server-side (E4: el cliente no lo manda).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import respx
from fastapi.testclient import TestClient

from app.api.routes import events as events_route

BASE = "https://sports.core.api.espn.com/v2"
LEAGUE = "ufc"
FIX = Path(__file__).parent / "fixtures" / "espn_ufc"
EVENT_ID = "600059148"


def _load(name: str) -> dict[str, Any]:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


@pytest.fixture(autouse=True)
def _reset_events_singletons():
    """Resetea los singletons module-level del router events entre tests."""
    events_route._provider = None
    events_route._resolver = None
    events_route._redis = None
    # Forzar también el path de Redis a fakeredis no aplica en estos tests
    # (no tocamos la caché real, la mockeamos vía fakeredis patch).
    yield
    events_route._provider = None
    events_route._resolver = None
    events_route._redis = None


@respx.mock
def test_list_events_returns_empty_image_url(client: TestClient) -> None:
    respx.get(url=f"{BASE}/sports/mma/leagues/{LEAGUE}/events?seasontype=2").respond(
        json=_load("event_list.json")
    )
    respx.get(url=f"{BASE}/sports/mma/leagues/{LEAGUE}/events/{EVENT_ID}").respond(
        json=_load(f"event_{EVENT_ID}.json")
    )

    resp = client.get("/api/events", params={"include_past_hours": 24 * 365})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) >= 1
    first = body[0]
    assert first["id"] == EVENT_ID
    assert first["name"].startswith("UFC 329")
    # D42: sin imagen de ESPN, el backend devuelve None (la app usa hero.webp).
    assert first["image_url"] is None


@respx.mock
def test_get_event_detail_derives_previous_bout_id(client: TestClient) -> None:
    """E4 — `previous_bout_id` se calcula server-side (matchNumber+1)."""
    respx.get(url=f"{BASE}/sports/mma/leagues/{LEAGUE}/events/{EVENT_ID}").respond(
        json=_load(f"event_{EVENT_ID}.json")
    )

    resp = client.get(f"/api/events/{EVENT_ID}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == EVENT_ID
    bouts = body["bouts"]
    assert len(bouts) == 14

    # main_event (matchNumber 1) tiene previous_bout_id = bout del matchNumber 2
    main = next(b for b in bouts if b["match_number"] == 1)
    bout_2 = next(b for b in bouts if b["match_number"] == 2)
    assert main["previous_bout_id"] == bout_2["id"]

    # El último bout de la card (matchNumber 14) no tiene previo.
    last = next(b for b in bouts if b["match_number"] == 14)
    assert last["previous_bout_id"] is None

    # Cada bout trae red y blue con headshot (resueltos vía AthleteResolver).
    # El fixture no mockea /athletes/, así que los resuelve con fallback CDN.
    assert "red" in bouts[0]
    assert "blue" in bouts[0]


def test_get_event_detail_returns_503_when_provider_fails(client: TestClient) -> None:
    """Si el provider está caído, 503 Service Unavailable (no 500)."""
    # Sin respx.mock → httpx intenta la red real y falla → el router captura.
    resp = client.get("/api/events/does-not-exist")
    assert resp.status_code == 503
