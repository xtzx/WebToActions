from __future__ import annotations

import json
import time
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
            body=b'{"amount":108,"currency":"CNY","approver":"alice"}',
            resource_type="xhr",
            is_navigation_request=False,
        )
        self.callbacks.on_response(
            request_id="req-1",
            status=200,
            status_text="OK",
            headers=[("content-type", "application/json")],
            body=b'{"expenseId":"exp-1","status":"submitted"}',
        )
        self.callbacks.on_navigation(
            url="https://example.com/expense/confirm",
            title="报销确认页",
        )

    def stop(self) -> dict[str, object]:
        self.callbacks.on_download(
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
        callbacks = kwargs["callbacks"]
        return FakeRecordingHandle(callbacks=callbacks)


def build_test_client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    data_dir = tmp_path / ".webtoactions"
    monkeypatch.setenv("WEBTOACTIONS_DATA_DIR", str(data_dir))
    get_settings.cache_clear()
    app = create_app(browser_bridge_factory=lambda _settings: FakePlaywrightBridge())
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


def wait_for_completed_review_context(
    client: TestClient,
    recording_id: str,
) -> dict[str, object]:
    for _ in range(20):
        response = client.get(f"/api/reviews/{recording_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["analysisStatus"] == "completed" and payload["latestDraft"] is not None:
            return payload
        time.sleep(0.05)

    raise AssertionError("Review analysis did not complete in time.")


def test_review_flow_rejects_analysis_before_recording_finishes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        session_id = client.post("/api/sessions", json={}).json()["id"]
        recording_id = client.post(
            "/api/recordings",
            json={
                "name": "提交报销单",
                "startUrl": "https://example.com/expense/new",
                "browserSessionId": session_id,
            },
        ).json()["id"]

        context_response = client.get(f"/api/reviews/{recording_id}")
        assert context_response.status_code == 409
        assert "recording" in context_response.json()["detail"]

        analysis_response = client.post(f"/api/reviews/{recording_id}/analysis")
        assert analysis_response.status_code == 409
        assert "recording" in analysis_response.json()["detail"]

        events_response = client.get(f"/api/reviews/{recording_id}/events?once=1")
        assert events_response.status_code == 409
        assert "recording" in events_response.json()["detail"]

    get_settings.cache_clear()


def test_review_flow_generates_metadata_draft_and_stream_snapshot(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        recording_id = create_stopped_recording(client)
        context = wait_for_completed_review_context(client, recording_id)

        assert context["recordingId"] == recording_id
        assert context["analysisStatus"] == "completed"
        assert context["latestDraft"]["version"] == 1
        assert context["latestDraft"]["candidateRequestIds"] == ["req-1"]
        assert context["latestDraft"]["parameterSuggestions"][0]["name"] == "amount"
        assert context["latestDraft"]["parameterSuggestions"][0]["source"] == "request.body.amount"
        assert context["latestDraft"]["actionFragmentSuggestions"][0]["stageId"] == "stage-1"
        assert context["latestReviewedMetadata"] is None
        assert len(context["requests"]) == 1
        assert len(context["pageStages"]) == 2

        with client.stream(
            "GET",
            f"/api/reviews/{recording_id}/events?once=1",
            headers={"accept": "text/event-stream"},
        ) as stream_response:
            assert stream_response.status_code == 200

            data_line = None
            for line in stream_response.iter_lines():
                if line.startswith("data: "):
                    data_line = line[6:]
                    break

            assert data_line is not None
            snapshot = json.loads(data_line)
            assert snapshot["recordingId"] == recording_id
            assert snapshot["status"] == "completed"
            assert snapshot["latestDraftVersion"] == 1

    get_settings.cache_clear()


def test_review_flow_saves_reviewed_metadata_versions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        recording_id = create_stopped_recording(client)
        context = wait_for_completed_review_context(client, recording_id)
        draft = context["latestDraft"]

        save_v1 = client.post(
            f"/api/reviews/{recording_id}/reviewed-metadata",
            json={
                "reviewer": "alice",
                "sourceDraftId": draft["id"],
                "sourceDraftVersion": draft["version"],
                "keyRequestIds": ["req-1"],
                "noiseRequestIds": [],
                "fieldDescriptions": {
                    "amount": "报销金额",
                    "currency": "币种",
                },
                "parameterSourceMap": {
                    "amount": "request.body.amount",
                    "currency": "request.body.currency",
                },
                "actionStageIds": ["stage-1"],
                "riskFlags": ["包含人工审批"]
            },
        )
        assert save_v1.status_code == 201
        reviewed_v1 = save_v1.json()
        assert reviewed_v1["version"] == 1
        assert reviewed_v1["previousVersion"] is None
        assert reviewed_v1["sourceDraftId"] == draft["id"]
        assert reviewed_v1["noiseRequestIds"] == []

        save_v2 = client.post(
            f"/api/reviews/{recording_id}/reviewed-metadata",
            json={
                "reviewer": "alice",
                "sourceDraftId": draft["id"],
                "sourceDraftVersion": draft["version"],
                "keyRequestIds": ["req-1"],
                "noiseRequestIds": [],
                "fieldDescriptions": {
                    "amount": "报销金额（人民币）",
                    "currency": "币种",
                },
                "parameterSourceMap": {
                    "amount": "request.body.amount",
                    "currency": "request.body.currency",
                    "approver": "request.body.approver",
                },
                "actionStageIds": ["stage-1", "stage-2"],
                "riskFlags": []
            },
        )
        assert save_v2.status_code == 201
        reviewed_v2 = save_v2.json()
        assert reviewed_v2["version"] == 2
        assert reviewed_v2["previousVersion"] == 1
        assert reviewed_v2["fieldDescriptions"]["amount"] == "报销金额（人民币）"
        assert reviewed_v2["parameterSourceMap"]["approver"] == "request.body.approver"

        latest_context = client.get(f"/api/reviews/{recording_id}")
        assert latest_context.status_code == 200
        latest_payload = latest_context.json()
        assert latest_payload["latestReviewedMetadata"]["version"] == 2
        assert [item["version"] for item in latest_payload["reviewHistory"]] == [2, 1]

    get_settings.cache_clear()


def test_review_flow_rejects_invalid_review_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        recording_id = create_stopped_recording(client)
        context = wait_for_completed_review_context(client, recording_id)
        draft = context["latestDraft"]

        invalid_response = client.post(
            f"/api/reviews/{recording_id}/reviewed-metadata",
            json={
                "reviewer": "alice",
                "sourceDraftId": draft["id"],
                "sourceDraftVersion": draft["version"],
                "keyRequestIds": ["req-1"],
                "noiseRequestIds": ["req-1"],
                "fieldDescriptions": {
                    "amount": "报销金额",
                },
                "parameterSourceMap": {
                    "amount": "request.body.amount",
                },
                "actionStageIds": ["stage-missing"],
                "riskFlags": []
            },
        )
        assert invalid_response.status_code == 400
        assert "noise" in invalid_response.json()["detail"]

    get_settings.cache_clear()
