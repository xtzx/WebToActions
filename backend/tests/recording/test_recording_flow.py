from __future__ import annotations

import json
from dataclasses import dataclass
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


@dataclass
class FakeRecordingHandle:
    callbacks: FakeRecordingCallbacks

    def __post_init__(self) -> None:
        self.callbacks.on_navigation(
            url="https://example.com/expense/new",
            title="报销创建页",
        )
        self.callbacks.on_request(
            request_id="req-1",
            method="POST",
            url="https://example.com/api/expenses",
            headers=[("content-type", "application/json")],
            body=b'{"amount":108,"currency":"CNY"}',
            resource_type="xhr",
            is_navigation_request=False,
        )
        self.callbacks.on_response(
            request_id="req-1",
            status=200,
            status_text="OK",
            headers=[("content-type", "application/json")],
            body=b'{"status":"ok"}',
        )
        self.callbacks.on_navigation(
            url="https://example.com/expense/confirm",
            title="报销确认页",
        )
        self.callbacks.on_upload(
            transfer_id="upload-1",
            file_name="invoice.pdf",
            related_request_id="req-1",
        )
        self.callbacks.on_download(
            transfer_id="download-1",
            file_name="receipt.pdf",
            related_request_id="req-1",
        )

    def stop(self) -> dict[str, object]:
        return {
            "currentUrl": "https://example.com/expense/confirm",
            "pageTitle": "报销确认页",
            "cookieSummary": {"count": "1", "domains": "example.com"},
            "storageSummary": {
                "localStorage": {
                    "itemCount": "1",
                    "blobKey": "evidence/rec_recording-1/session_state/snapshot-1.json",
                }
            },
            "loginSiteSummaries": ["example.com"],
        }


class FakePlaywrightBridge:
    def start_recording(self, **kwargs) -> FakeRecordingHandle:  # type: ignore[no-untyped-def]
        callbacks = kwargs["callbacks"]
        return FakeRecordingHandle(callbacks=callbacks)


@dataclass
class FailFirstStopRecordingHandle(FakeRecordingHandle):
    stop_attempts: int = 0

    def stop(self) -> dict[str, object]:
        self.stop_attempts += 1
        if self.stop_attempts == 1:
            raise RuntimeError("simulated browser stop failure")
        return super().stop()


class FailFirstStopBridge:
    def start_recording(self, **kwargs) -> FailFirstStopRecordingHandle:  # type: ignore[no-untyped-def]
        callbacks = kwargs["callbacks"]
        return FailFirstStopRecordingHandle(callbacks=callbacks)


def build_test_client(
    tmp_path: Path,
    monkeypatch,
    *,
    browser_bridge_factory=None,
    raise_server_exceptions: bool = True,
) -> TestClient:  # type: ignore[no-untyped-def]
    data_dir = tmp_path / ".webtoactions"
    monkeypatch.setenv("WEBTOACTIONS_DATA_DIR", str(data_dir))
    get_settings.cache_clear()
    app = create_app(
        browser_bridge_factory=browser_bridge_factory
        or (lambda _settings: FakePlaywrightBridge())
    )
    return TestClient(app, raise_server_exceptions=raise_server_exceptions)


def test_sessions_api_creates_and_lists_managed_browser_sessions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        response = client.post("/api/sessions", json={})
        assert response.status_code == 201
        payload = response.json()

        assert payload["status"] == "available"
        assert payload["profileId"].startswith("profile-")
        assert payload["loginSiteSummaries"] == []

        list_response = client.get("/api/sessions")
        assert list_response.status_code == 200
        assert list_response.json()["items"] == [payload]

    get_settings.cache_clear()


def test_recording_api_starts_stops_and_exposes_detail_and_sse(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / ".webtoactions"

    with build_test_client(tmp_path, monkeypatch) as client:
        session_response = client.post("/api/sessions", json={})
        session_id = session_response.json()["id"]

        start_response = client.post(
            "/api/recordings",
            json={
                "name": "提交报销单",
                "startUrl": "https://example.com/expense/new",
                "browserSessionId": session_id,
            },
        )
        assert start_response.status_code == 201
        started = start_response.json()

        assert started["status"] == "recording"
        assert started["browserSessionId"] == session_id
        assert started["requestCount"] == 1
        assert started["pageStageCount"] == 2
        assert started["fileTransferCount"] == 2
        assert started["currentUrl"] == "https://example.com/expense/confirm"

        with client.stream(
            "GET",
            f"/api/recordings/{started['id']}/events?once=1",
            headers={"accept": "text/event-stream"},
        ) as stream_response:
            assert stream_response.status_code == 200
            assert stream_response.headers["content-type"].startswith("text/event-stream")

            data_line = None
            for line in stream_response.iter_lines():
                if line.startswith("data: "):
                    data_line = line[6:]
                    break

            assert data_line is not None
            snapshot = json.loads(data_line)
            assert snapshot["recordingId"] == started["id"]
            assert snapshot["status"] == "recording"
            assert snapshot["requestCount"] == 1
            assert snapshot["pageStageCount"] == 2

        stop_response = client.post(f"/api/recordings/{started['id']}/stop")
        assert stop_response.status_code == 200
        detail = stop_response.json()

        assert detail["status"] == "pending_review"
        assert len(detail["pageStages"]) == 2
        assert len(detail["requests"]) == 1
        assert len(detail["sessionSnapshots"]) == 1
        assert len(detail["fileTransfers"]) == 2

        request_record = detail["requests"][0]
        assert request_record["requestBodyBlobKey"].endswith("request-body.bin")
        assert request_record["responseBodyBlobKey"].endswith("response-body.bin")
        assert (data_dir / request_record["requestBodyBlobKey"]).exists()
        assert (data_dir / request_record["responseBodyBlobKey"]).exists()

        list_response = client.get("/api/recordings")
        assert list_response.status_code == 200
        assert list_response.json()["items"][0]["status"] == "pending_review"

        detail_response = client.get(f"/api/recordings/{started['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json() == detail

    get_settings.cache_clear()


def test_recording_api_returns_not_found_for_unknown_browser_session(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(
        tmp_path,
        monkeypatch,
        raise_server_exceptions=False,
    ) as client:
        response = client.post(
            "/api/recordings",
            json={
                "name": "提交报销单",
                "startUrl": "https://example.com/expense/new",
                "browserSessionId": "session-missing",
            },
        )

        assert response.status_code == 404
        assert "does not exist" in response.json()["detail"]

    get_settings.cache_clear()


def test_recording_stop_failure_keeps_runtime_available_for_retry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(
        tmp_path,
        monkeypatch,
        browser_bridge_factory=lambda _settings: FailFirstStopBridge(),
        raise_server_exceptions=False,
    ) as client:
        session_id = client.post("/api/sessions", json={}).json()["id"]
        start_response = client.post(
            "/api/recordings",
            json={
                "name": "提交报销单",
                "startUrl": "https://example.com/expense/new",
                "browserSessionId": session_id,
            },
        )
        recording_id = start_response.json()["id"]

        failed_stop = client.post(f"/api/recordings/{recording_id}/stop")
        assert failed_stop.status_code == 500

        detail_after_failure = client.get(f"/api/recordings/{recording_id}")
        assert detail_after_failure.status_code == 200
        assert detail_after_failure.json()["status"] == "recording"

        retried_stop = client.post(f"/api/recordings/{recording_id}/stop")
        assert retried_stop.status_code == 200
        assert retried_stop.json()["status"] == "pending_review"

    get_settings.cache_clear()
