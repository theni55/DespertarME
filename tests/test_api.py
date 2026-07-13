"""Tests de integración de la API REST + admin web (Fase 3).

Usa TestClient con BD SQLite en memoria overrideando `get_session`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# --- Auth: registro y login --------------------------------------------------


def test_register_returns_token(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/auth/register",
        json={
            "email": "alice@example.com",
            "password": "mypassword123",
            "phone": "+34600000000",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == "user"


def test_register_duplicate_email_fails(app_client: TestClient) -> None:
    payload = {"email": "bob@example.com", "password": "mypassword123", "phone": "+34600000001"}
    app_client.post("/api/auth/register", json=payload)
    resp = app_client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_invalid_phone_fails(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/auth/register",
        json={"email": "badphone@example.com", "password": "mypassword123", "phone": "600123"},
    )
    assert resp.status_code == 422


def test_register_without_phone_fails(app_client: TestClient) -> None:
    resp = app_client.post(
        "/api/auth/register",
        json={"email": "nophone@example.com", "password": "mypassword123"},
    )
    assert resp.status_code == 422


def test_login_returns_token(app_client: TestClient) -> None:
    app_client.post(
        "/api/auth/register",
        json={"email": "carol@example.com", "password": "mypassword123", "phone": "+34600000002"},
    )
    resp = app_client.post(
        "/api/auth/login",
        data={"username": "carol@example.com", "password": "mypassword123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password_fails(app_client: TestClient) -> None:
    app_client.post(
        "/api/auth/register",
        json={"email": "dave@example.com", "password": "correctpass123", "phone": "+34600000003"},
    )
    resp = app_client.post(
        "/api/auth/login",
        data={"username": "dave@example.com", "password": "wrongpass123"},
    )
    assert resp.status_code == 401


# --- Subscriptions -----------------------------------------------------------


def _auth_token(app_client: TestClient, email: str = "sub@example.com") -> str:
    app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "mypassword123", "phone": "+34600000009"},
    )
    resp = app_client.post(
        "/api/auth/login",
        data={"username": email, "password": "mypassword123"},
    )
    return resp.json()["access_token"]


def test_create_and_list_subscription(app_client: TestClient) -> None:
    token = _auth_token(app_client, "sub1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    resp = app_client.post(
        "/api/subscriptions",
        json={
            "event_id": "ev-1",
            "bout_id": "comp-1",
            "target_match_number": 1,
            "previous_bout_id": "comp-2",
            "previous_match_number": 2,
            "lead_minutes": 15,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    sub = resp.json()
    assert sub["event_id"] == "ev-1"
    assert sub["status"] == "active"

    resp = app_client.get("/api/subscriptions", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_delete_subscription(app_client: TestClient) -> None:
    token = _auth_token(app_client, "sub2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

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
    assert len(resp.json()) == 0


def test_subscriptions_require_auth(app_client: TestClient) -> None:
    resp = app_client.get("/api/subscriptions")
    assert resp.status_code == 401


# --- Users (solo admin) ------------------------------------------------------


def test_list_users_requires_admin(app_client: TestClient) -> None:
    token = _auth_token(app_client, "nonadmin@example.com")
    resp = app_client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# --- Alerts ------------------------------------------------------------------


def test_list_alerts_empty(app_client: TestClient) -> None:
    token = _auth_token(app_client, "alerts@example.com")
    resp = app_client.get("/api/alerts", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


# --- Meta endpoints siguen funcionando ---------------------------------------


def test_health_still_ok(app_client: TestClient) -> None:
    resp = app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
