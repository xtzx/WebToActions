from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.core import get_settings
from app.main import create_app


class FakeRecordingCallbacks:
    def on_navigation(self, *, url: str, title: str | None) -> None: ...

    def on_request(
        self,
        *,
        request_id: str,
        method: str,
        url: str,
        headers: list[tuple[str, str]],
        body: bytes | None,
        resource_type: str,
        is_navigation_request: bool,
    ) -> None: ...

    def on_response(
        self,
        *,
        request_id: str,
        status: int,
        status_text: str,
        headers: list[tuple[str, str]],
        body: bytes | None,
    ) -> None: ...

    def on_request_failed(self, *, request_id: str, reason: str) -> None: ...

    def on_upload(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None: ...

    def on_download(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None: ...


class FakeRecordingHandle:
    def __init__(self, callbacks: FakeRecordingCallbacks) -> None:
        self._callbacks = callbacks
        self._callbacks.on_navigation(
            url="https://example.com/expense/new",
            title="报销创建页",
        )
        self._callbacks.on_request(
            request_id="req-1",
            method="POST",
            url="https://example.com/api/expenses",
            headers=[("content-type", "application/json")],
            body=b'{"amount":108,"currency":"CNY","approver":"alice"}',
            resource_type="xhr",
            is_navigation_request=False,
        )
        self._callbacks.on_response(
            request_id="req-1",
            status=200,
            status_text="OK",
            headers=[("content-type", "application/json")],
            body=b'{"expenseId":"exp-1","status":"submitted"}',
        )
        self._callbacks.on_navigation(
            url="https://example.com/expense/confirm",
            title="报销确认页",
        )

    def stop(self) -> dict[str, object]:
        self._callbacks.on_download(
            transfer_id="download-1",
            file_name="receipt.pdf",
            related_request_id="req-1",
        )
        return {
            "currentUrl": "https://example.com/expense/confirm",
            "pageTitle": "报销确认页",
            "cookieSummary": {"count": "1", "domains": "example.com"},
            "storageSummary": {"localStorage": {"itemCount": "1"}},
            "loginSiteSummaries": ["example.com"],
        }


class FakePlaywrightBridge:
    def start_recording(self, **kwargs) -> FakeRecordingHandle:  # type: ignore[no-untyped-def]
        return FakeRecordingHandle(callbacks=kwargs["callbacks"])


class FakeBrowserReplayer:
    def replay(self, **kwargs) -> dict[str, object]:  # type: ignore[no-untyped-def]
        return {"finalUrl": "https://example.com/expense/confirm", "stepOutcomes": []}


class DummyBrowserBridge:
    pass


class DummyBrowserReplayer:
    pass


def build_test_client(data_dir: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("WEBTOACTIONS_DATA_DIR", str(data_dir))
    get_settings.cache_clear()
    app = create_app(
        browser_bridge_factory=lambda _settings: FakePlaywrightBridge(),
        browser_replayer_factory=lambda _settings: FakeBrowserReplayer(),
    )
    return TestClient(app)


def create_stopped_recording(client: TestClient) -> str:
    session_id = client.post("/api/sessions", json={}).json()["id"]
    recording_id = client.post(
        "/api/recordings",
        json={
            "name": "提交报销单",
            "startUrl": "https://example.com/expense/new",
            "browserSessionId": session_id,
        },
    ).json()["id"]
    stop_response = client.post(f"/api/recordings/{recording_id}/stop")
    assert stop_response.status_code == 200
    return recording_id


def wait_for_completed_review_context(client: TestClient, recording_id: str) -> dict[str, object]:
    for _ in range(20):
        response = client.get(f"/api/reviews/{recording_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["analysisStatus"] == "completed" and payload["latestDraft"] is not None:
            return payload
        time.sleep(0.05)

    raise AssertionError("Review analysis did not complete in time.")


def test_missing_resources_return_404_across_stage6_routes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path / "failure-data", monkeypatch) as client:
        assert client.get("/api/recordings/missing-recording").status_code == 404
        assert client.get("/api/reviews/missing-recording").status_code == 404
        assert client.post("/api/actions", json={"recordingId": "missing-recording"}).status_code == 404
        assert client.get("/api/actions/missing-action").status_code == 404
        assert client.get("/api/executions/missing-run").status_code == 404
        assert client.get("/api/importexport/recordings/missing-recording/bundle").status_code == 404

    get_settings.cache_clear()


def test_conflict_and_validation_paths_return_expected_status_codes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path / "failure-data", monkeypatch) as client:
        recording_id = create_stopped_recording(client)
        context = wait_for_completed_review_context(client, recording_id)

        action_conflict = client.post("/api/actions", json={"recordingId": recording_id})
        assert action_conflict.status_code == 409

        invalid_recording = client.post(
            "/api/recordings",
            json={"name": "", "startUrl": "", "browserSessionId": "session-1"},
        )
        assert invalid_recording.status_code == 422

        invalid_review_payload = client.post(
            f"/api/reviews/{recording_id}/reviewed-metadata",
            json={
                "reviewer": "",
                "sourceDraftId": context["latestDraft"]["id"],
                "sourceDraftVersion": context["latestDraft"]["version"],
            },
        )
        assert invalid_review_payload.status_code == 422

        missing_bundle_file = client.post("/api/importexport/recordings/import")
        assert missing_bundle_file.status_code == 422

    get_settings.cache_clear()


def test_runtime_mode_keeps_missing_assets_and_unknown_api_routes_as_404(
    tmp_path: Path,
    monkeypatch,
) -> None:
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    (dist_dir / "index.html").write_text(
        "<!doctype html><html><body><div id='root'>Runtime</div></body></html>",
        encoding="utf-8",
    )

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
        missing_asset = client.get("/assets/missing.js")
        assert missing_asset.status_code == 404

        missing_api_route = client.get("/api/unknown")
        assert missing_api_route.status_code == 404
        assert "text/html" not in (missing_api_route.headers.get("content-type") or "")

    get_settings.cache_clear()
