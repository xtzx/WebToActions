import pytest
from fastapi.testclient import TestClient

from app.api.routes import health as health_module
from app.core.config import Settings, get_settings
import app.main as main_module
from app.main import create_app


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "APP_NAME",
        "APP_ENV",
        "API_PREFIX",
        "WEBTOACTIONS_DATA_DIR",
        "FRONTEND_DEV_ORIGIN",
        "BROWSER_CHANNEL",
        "BROWSER_HEADLESS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    get_settings.cache_clear()
    monkeypatch.setattr(main_module, "get_settings", lambda: settings)
    monkeypatch.setattr(health_module, "get_settings", lambda: settings)


def test_health_endpoint_returns_formal_contract() -> None:
    client = TestClient(create_app())

    response = client.get("/api/health")

    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["phase"] == "stage1"
    assert payload["appName"] == "WebToActions Backend"
    assert payload["environment"] == "development"
    assert payload["apiPrefix"] == "/api"
    assert payload["targetPython"] == "3.11+"
    assert payload["dataDir"] == ".webtoactions"
    assert payload["browserChannel"] == "chromium"
    assert payload["browserHeadless"] is False
    assert isinstance(payload["runtimePython"], str)


def test_create_app_uses_settings_app_name_as_title() -> None:
    assert create_app().title == "WebToActions Backend"
