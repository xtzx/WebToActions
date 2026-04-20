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
        return FakeRecordingHandle(callbacks=kwargs["callbacks"])


class FakeBrowserReplayer:
    def replay(self, **kwargs) -> dict[str, object]:  # type: ignore[no-untyped-def]
        steps = kwargs["steps"]
        callbacks = kwargs["callbacks"]

        for step in steps:
            callbacks.on_log(
                message=f"开始执行 {step.title}",
                step_id=step.id,
                step_title=step.title,
                current_url=step.navigate_url,
            )
            callbacks.on_log(
                message=f"完成执行 {step.title}",
                step_id=step.id,
                step_title=step.title,
                current_url=step.navigate_url,
            )

        first_step = steps[0]
        if first_step.request_body_text and '"amount": 0' in first_step.request_body_text:
            raise RuntimeError(f"步骤失败：{first_step.title}")

        return {
            "finalUrl": steps[-1].navigate_url,
            "stepOutcomes": [
                {
                    "stepId": step.id,
                    "requestId": step.request_id,
                    "requestBodyPreview": step.request_body_text,
                    "responseStatus": 200,
                }
                for step in steps
            ],
        }


def build_test_client(tmp_path: Path, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    data_dir = tmp_path / ".webtoactions"
    monkeypatch.setenv("WEBTOACTIONS_DATA_DIR", str(data_dir))
    get_settings.cache_clear()
    app = create_app(
        browser_bridge_factory=lambda _settings: FakePlaywrightBridge(),
        browser_replayer_factory=lambda _settings: FakeBrowserReplayer(),
    )
    return TestClient(app)


def create_stopped_recording(client: TestClient) -> tuple[str, str]:
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
    return recording_id, session_id


def wait_for_completed_review_context(client: TestClient, recording_id: str) -> dict[str, object]:
    for _ in range(20):
        response = client.get(f"/api/reviews/{recording_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["analysisStatus"] == "completed" and payload["latestDraft"] is not None:
            return payload
        time.sleep(0.05)

    raise AssertionError("Review analysis did not complete in time.")


def create_reviewed_recording(client: TestClient) -> tuple[str, str]:
    recording_id, session_id = create_stopped_recording(client)
    context = wait_for_completed_review_context(client, recording_id)
    draft = context["latestDraft"]
    save_response = client.post(
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
            "riskFlags": ["包含人工审批"],
        },
    )
    assert save_response.status_code == 201
    return recording_id, session_id


def wait_for_execution_terminal_detail(
    client: TestClient,
    execution_id: str,
) -> dict[str, object]:
    for _ in range(20):
        response = client.get(f"/api/executions/{execution_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"succeeded", "failed"}:
            return payload
        time.sleep(0.05)

    raise AssertionError("Execution did not reach a terminal state in time.")


def test_actions_api_rejects_generation_without_reviewed_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        recording_id, _session_id = create_stopped_recording(client)

        response = client.post("/api/actions", json={"recordingId": recording_id})

        assert response.status_code == 409
        assert "reviewed metadata" in response.json()["detail"].lower()

    get_settings.cache_clear()


def test_action_and_execution_flow_generates_macro_runs_execution_and_streams_logs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        recording_id, session_id = create_reviewed_recording(client)

        action_response = client.post("/api/actions", json={"recordingId": recording_id})
        assert action_response.status_code == 201
        action_payload = action_response.json()
        assert action_payload["version"] == 1
        assert action_payload["recordingId"] == recording_id
        assert action_payload["steps"][0]["requestId"] == "req-1"
        assert action_payload["parameterDefinitions"][0]["name"] == "amount"
        assert action_payload["parameterDefinitions"][0]["injectionTarget"] == "request.body.amount"

        recording_detail = client.get(f"/api/recordings/{recording_id}")
        assert recording_detail.status_code == 200
        assert recording_detail.json()["status"] == "macro_generated"

        execution_response = client.post(
            f"/api/actions/{action_payload['id']}/executions",
            json={
                "browserSessionId": session_id,
                "parameters": {
                    "amount": 208,
                    "currency": "USD",
                },
            },
        )
        assert execution_response.status_code == 201
        execution_payload = execution_response.json()
        execution_id = execution_payload["id"]

        terminal_detail = wait_for_execution_terminal_detail(client, execution_id)
        assert terminal_detail["status"] == "succeeded"
        assert terminal_detail["diagnostics"]["stepOutcomes"][0]["responseStatus"] == 200
        assert '"amount": 208' in terminal_detail["diagnostics"]["stepOutcomes"][0]["requestBodyPreview"]
        assert len(terminal_detail["stepLogs"]) >= 2

        actions_list = client.get("/api/actions")
        assert actions_list.status_code == 200
        assert actions_list.json()["items"][0]["id"] == action_payload["id"]

        executions_list = client.get("/api/executions")
        assert executions_list.status_code == 200
        assert executions_list.json()["items"][0]["id"] == execution_id

        with client.stream(
            "GET",
            f"/api/executions/{execution_id}/events?once=1",
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
            assert snapshot["executionId"] == execution_id
            assert snapshot["status"] == "succeeded"
            assert snapshot["logCount"] >= 2

    get_settings.cache_clear()


def test_execution_flow_reports_failed_step_when_replay_raises(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with build_test_client(tmp_path, monkeypatch) as client:
        recording_id, session_id = create_reviewed_recording(client)
        action_payload = client.post(
            "/api/actions",
            json={"recordingId": recording_id},
        ).json()

        execution_response = client.post(
            f"/api/actions/{action_payload['id']}/executions",
            json={
                "browserSessionId": session_id,
                "parameters": {
                    "amount": 0,
                    "currency": "USD",
                },
            },
        )
        assert execution_response.status_code == 201
        execution_id = execution_response.json()["id"]

        terminal_detail = wait_for_execution_terminal_detail(client, execution_id)
        assert terminal_detail["status"] == "failed"
        assert "步骤失败" in terminal_detail["failureReason"]
        assert terminal_detail["diagnostics"]["failedStepId"] == "step-1"
        assert terminal_detail["diagnostics"]["failedStepTitle"]

    get_settings.cache_clear()
