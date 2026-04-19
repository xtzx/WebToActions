from pathlib import Path

from fastapi.testclient import TestClient

from app.core import get_settings
from app.main import create_app


def test_app_lifespan_initializes_storage_runtime_and_repository(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / ".webtoactions"
    monkeypatch.setenv("WEBTOACTIONS_DATA_DIR", str(data_dir))
    get_settings.cache_clear()

    app = create_app()

    with TestClient(app):
        assert app.state.storage_layout.root == data_dir
        assert app.state.storage_layout.evidence_root.is_dir()
        assert app.state.storage_layout.actions_root.is_dir()
        assert app.state.sqlite_runtime.database_path == data_dir / "app.db"
        assert app.state.sqlite_runtime.database_path.exists()
        assert app.state.recording_repository is not None

    get_settings.cache_clear()
