"""Tests de integración de la API REST (Fase 7a, device model).

Usa TestClient con BD SQLite en memoria overrideando `get_session`. La auth es
vía header `X-Device-Id` (sin JWT/register/login).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# --- Devices: registro y test-alarm -----------------------------------------


def _register_device(
    app_client: TestClient,
    device_id: str = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    fcm_token: str = "fake-fcm-token-1234567890",
    platform: str = "android",
) -> dict:
    resp = app_client.post(
        "/api/devices",
        json={
            "device_id": device_id,
            "fcm_token": fcm_token,
            "platform": platform,
            "timezone": "Europe/Madrid",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_register_device_returns_device(app_client: TestClient) -> None:
    body = _register_device(app_client)
    assert body["id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert body["fcm_token"] == "fake-fcm-token-1234567890"
    assert body["platform"] == "android"
    assert body["is_active"] is True
    assert body["timezone"] == "Europe/Madrid"


def test_register_device_upsert_updates_token(app_client: TestClient) -> None:
    _register_device(app_client)
    # Segundo registro con mismo id + token nuevo → upsert
    resp = app_client.post(
        "/api/devices",
        json={
            "device_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
            "fcm_token": "new-token-9876543210",
            "platform": "android",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["fcm_token"] == "new-token-9876543210"


def test_register_invalid_device_id_rejected(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/devices",
        json={"device_id": "x", "fcm_token": "tok-1234567890"},
    )
    assert resp.status_code == 422


# --- Subscriptions (require X-Device-Id) ------------------------------------


def _headers(device_id: str) -> dict:
    return {"X-Device-Id": device_id}


def test_create_and_list_subscription(app_client: TestClient) -> None:
    _register_device(app_client)
    headers = _headers("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    resp = app_client.post(
        "/api/subscriptions",
        json={
            "event_id": "ev-1",
            "bout_id": "comp-1",
            "target_match_number": 1,
            "lead_minutes": 15,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    sub = resp.json()
    assert sub["event_id"] == "ev-1"
    assert sub["bout_id"] == "comp-1"
    assert sub["status"] == "active"
    assert sub["device_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    assert "previous_bout_id" not in sub  # E4: el cliente no lo manda
    assert "user_id" not in sub

    resp = app_client.get("/api/subscriptions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_subscription_lead_minutes_minimum(app_client: TestClient) -> None:
    """E2 sin arreglar del todo → el backend exige lead_minutes >= 5."""
    _register_device(app_client)
    headers = _headers("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    resp = app_client.post(
        "/api/subscriptions",
        json={
            "event_id": "ev-1",
            "bout_id": "comp-1",
            "target_match_number": 1,
            "lead_minutes": 2,
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_create_subscription_rejects_duplicated_bout(app_client: TestClient) -> None:
    """E6: UNIQUE (device_id, bout_id) impide re-suscribirse al mismo combate."""
    _register_device(app_client)
    headers = _headers("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    body = {
        "event_id": "ev-1",
        "bout_id": "comp-1",
        "target_match_number": 1,
        "lead_minutes": 10,
    }
    r1 = app_client.post("/api/subscriptions", json=body, headers=headers)
    assert r1.status_code == 201
    r2 = app_client.post("/api/subscriptions", json=body, headers=headers)
    assert r2.status_code == 409


def test_delete_subscription(app_client: TestClient) -> None:
    _register_device(app_client)
    headers = _headers("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")

    resp = app_client.post(
        "/api/subscriptions",
        json={
            "event_id": "ev-1",
            "bout_id": "comp-1",
            "target_match_number": 1,
        },
        headers=headers,
    )
    sub_id = resp.json()["id"]

    resp = app_client.delete(f"/api/subscriptions/{sub_id}", headers=headers)
    assert resp.status_code == 204

    resp = app_client.get("/api/subscriptions", headers=headers)
    assert resp.json() == []


def test_subscriptions_require_device_header(app_client: TestClient) -> None:
    resp = app_client.get("/api/subscriptions")
    assert resp.status_code == 401


def test_subscriptions_unknown_device_unauthorized(app_client: TestClient) -> None:
    resp = app_client.get(
        "/api/subscriptions", headers={"X-Device-Id": "00000000-0000-0000-0000-000000000000"}
    )
    assert resp.status_code == 401


def test_device_header_is_case_insensitive(app_client: TestClient) -> None:
    """Regresión (review Fase 7a): el registro normaliza el device_id a
    minúsculas, así que la auth debe aceptar el UUID en mayúsculas también."""
    _register_device(app_client, device_id="AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE")
    resp = app_client.get(
        "/api/subscriptions",
        headers={"X-Device-Id": "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_deactivate_device_me(app_client: TestClient) -> None:
    _register_device(app_client)
    headers = _headers("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    resp = app_client.delete("/api/devices/me", headers=headers)
    assert resp.status_code == 204
    # Siguiente request con el mismo header → 403 (inactivo)
    resp = app_client.get("/api/subscriptions", headers=headers)
    assert resp.status_code == 403


# --- Alerts ----------------------------------------------------------------


def test_list_alerts_empty(app_client: TestClient) -> None:
    _register_device(app_client)
    headers = _headers("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    resp = app_client.get("/api/alerts", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_alerts_require_device_header(app_client: TestClient) -> None:
    resp = app_client.get("/api/alerts")
    assert resp.status_code == 401


# --- test-alarm -------------------------------------------------------------


def test_test_alarm_requires_registered_device(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/devices/me/test-alarm",
        headers={"X-Device-Id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 401


def test_test_alarm_calls_notifier(app_client: TestClient) -> None:
    """Sin FCM configurado, build_notifier devuelve DummyNotifier: test-alarm success."""
    _register_device(app_client)
    headers = _headers("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    resp = app_client.post("/api/devices/me/test-alarm", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True


# --- Meta endpoints siguen funcionando -------------------------------------


def test_health_still_ok(app_client: TestClient) -> None:
    resp = app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
