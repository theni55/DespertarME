from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_root_serves_landing(client: TestClient) -> None:
    """La landing pública (D35/D36) se sirve siempre en `/`, sin redirigir."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "Avísame" in response.text
