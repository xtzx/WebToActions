from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core import get_settings
from app.main import create_app


class DummyBrowserBridge:
    pass


class DummyBrowserReplayer:
    pass


def test_runtime_mode_serves_frontend_index_spa_fallback_and_health_api(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dist_dir = tmp_path / "dist"
    assets_dir = dist_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>WebToActions Runtime</div></body></html>",
        encoding="utf-8",
    )
    (assets_dir / "app.js").write_text("console.log('runtime asset');", encoding="utf-8")

    data_dir = tmp_path / ".webtoactions"
    monkeypatch.setenv("WEBTOACTIONS_DATA_DIR", str(data_dir))
    monkeypatch.setenv("FRONTEND_STATIC_ENABLED", "true")
    monkeypatch.setenv("FRONTEND_DIST_DIR", str(dist_dir))
    get_settings.cache_clear()

    app = create_app(
        browser_bridge_factory=lambda _settings: DummyBrowserBridge(),
        browser_replayer_factory=lambda _settings: DummyBrowserReplayer(),
    )

    with TestClient(app) as client:
        index_response = client.get("/")
        assert index_response.status_code == 200
        assert "WebToActions Runtime" in index_response.text

        asset_response = client.get("/assets/app.js")
        assert asset_response.status_code == 200
        assert "runtime asset" in asset_response.text

        route_response = client.get("/recordings/recording-1")
        assert route_response.status_code == 200
        assert "WebToActions Runtime" in route_response.text

        health_response = client.get("/api/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] == "ok"

    get_settings.cache_clear()
