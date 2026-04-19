from pathlib import Path

import pytest

from app.core.config import REPO_ROOT, Settings


@pytest.fixture(autouse=True)
def clear_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_settings_uses_expected_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "WebToActions Backend"
    assert settings.app_env == "development"
    assert settings.api_prefix == "/api"
    assert settings.frontend_dev_origin == "http://127.0.0.1:5173"
    assert settings.target_python == "3.11+"
    assert settings.webtoactions_data_dir == REPO_ROOT / ".webtoactions"
    assert settings.data_dir_display == str(Path(".webtoactions"))
    assert settings.browser_channel == "chromium"
    assert settings.browser_headless is False
