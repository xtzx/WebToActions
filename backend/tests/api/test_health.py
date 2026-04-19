from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["stage"] == "spike"


def test_spike_context_reports_runtime_constraints() -> None:
    client = TestClient(create_app())

    response = client.get("/api/spike/context")

    assert response.status_code == 200

    payload = response.json()
    assert payload["stage"] == "spike"
    assert payload["targetPython"] == "3.11+"
    assert payload["browserEngine"] == "playwright"
