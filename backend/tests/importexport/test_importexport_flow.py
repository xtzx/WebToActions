from __future__ import annotations

from io import BytesIO
import json
import time
from zipfile import ZipFile

from fastapi.testclient import TestClient
import pytest

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


def build_test_client(data_dir, monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("WEBTOACTIONS_DATA_DIR", str(data_dir))
    get_settings.cache_clear()
    app = create_app(
        browser_bridge_factory=lambda _settings: FakePlaywrightBridge(),
        browser_replayer_factory=lambda _settings: FakeBrowserReplayer(),
    )
    return TestClient(app)


def create_reviewed_recording(client: TestClient) -> tuple[str, str]:
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


def wait_for_completed_review_context(client: TestClient, recording_id: str) -> dict[str, object]:
    for _ in range(20):
        response = client.get(f"/api/reviews/{recording_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["analysisStatus"] == "completed" and payload["latestDraft"] is not None:
            return payload
        time.sleep(0.05)

    raise AssertionError("Review analysis did not complete in time.")


def wait_for_terminal_execution(client: TestClient, execution_id: str) -> dict[str, object]:
    for _ in range(20):
        response = client.get(f"/api/executions/{execution_id}")
        assert response.status_code == 200
        payload = response.json()
        if payload["status"] in {"succeeded", "failed"}:
            return payload
        time.sleep(0.05)

    raise AssertionError("Execution did not reach a terminal state in time.")


def test_importexport_exports_recording_bundle_and_imports_it_without_login_state(
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source-data"
    target_dir = tmp_path / "target-data"

    with build_test_client(source_dir, monkeypatch) as source_client:
        recording_id, session_id = create_reviewed_recording(source_client)

        action_response = source_client.post("/api/actions", json={"recordingId": recording_id})
        assert action_response.status_code == 201
        action_id = action_response.json()["id"]

        execution_response = source_client.post(
            f"/api/actions/{action_id}/executions",
            json={
                "browserSessionId": session_id,
                "parameters": {
                    "amount": "208",
                    "currency": "USD",
                },
            },
        )
        assert execution_response.status_code == 201
        execution_id = execution_response.json()["id"]
        wait_for_terminal_execution(source_client, execution_id)

        detail_response = source_client.get(f"/api/recordings/{recording_id}")
        assert detail_response.status_code == 200
        request_body_blob_key = detail_response.json()["requests"][0]["requestBodyBlobKey"]

        export_response = source_client.get(f"/api/importexport/recordings/{recording_id}/bundle")

        assert export_response.status_code == 200
        assert export_response.headers["content-type"] == "application/zip"

        archive_entries = set(ZipFile(BytesIO(export_response.content)).namelist())
        assert "manifest.json" in archive_entries
        assert "recording-aggregate.json" in archive_entries
        assert request_body_blob_key in archive_entries
        assert f"actions/macro_{action_id}/version_1.json" in archive_entries
        assert f"runs/run_{execution_id}/run.json" in archive_entries

    with build_test_client(target_dir, monkeypatch) as target_client:
        import_response = target_client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "recording-bundle.zip",
                    export_response.content,
                    "application/zip",
                )
            },
        )

        assert import_response.status_code == 201
        payload = import_response.json()
        assert payload["recordingId"] == recording_id
        assert payload["actionIds"] == [action_id]
        assert payload["executionIds"] == [execution_id]
        assert "登录态" in payload["warnings"][0]

        imported_recording = target_client.get(f"/api/recordings/{recording_id}")
        assert imported_recording.status_code == 200
        assert imported_recording.json()["status"] == "macro_generated"

        imported_action = target_client.get(f"/api/actions/{action_id}")
        assert imported_action.status_code == 200
        assert imported_action.json()["recordingId"] == recording_id

        imported_execution = target_client.get(f"/api/executions/{execution_id}")
        assert imported_execution.status_code == 200
        assert imported_execution.json()["status"] == "succeeded"

        sessions_response = target_client.get("/api/sessions")
        assert sessions_response.status_code == 200
        assert sessions_response.json()["items"][0]["id"] == session_id
        assert sessions_response.json()["items"][0]["status"] == "relogin_required"
        assert sessions_response.json()["items"][0]["loginSiteSummaries"] == []


def test_importexport_exports_historical_action_versions_referenced_by_execution_runs(
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source-data"
    target_dir = tmp_path / "target-data"

    with build_test_client(source_dir, monkeypatch) as source_client:
        recording_id, session_id = create_reviewed_recording(source_client)

        first_action_response = source_client.post("/api/actions", json={"recordingId": recording_id})
        assert first_action_response.status_code == 201
        action_id = first_action_response.json()["id"]
        assert first_action_response.json()["version"] == 1

        first_execution_response = source_client.post(
            f"/api/actions/{action_id}/executions",
            json={
                "browserSessionId": session_id,
                "parameters": {
                    "amount": "208",
                    "currency": "USD",
                },
            },
        )
        assert first_execution_response.status_code == 201
        execution_id = first_execution_response.json()["id"]
        wait_for_terminal_execution(source_client, execution_id)

        second_action_response = source_client.post("/api/actions", json={"recordingId": recording_id})
        assert second_action_response.status_code == 201
        assert second_action_response.json()["id"] == action_id
        assert second_action_response.json()["version"] == 2

        export_response = source_client.get(f"/api/importexport/recordings/{recording_id}/bundle")
        assert export_response.status_code == 200

        archive_entries = set(ZipFile(BytesIO(export_response.content)).namelist())
        assert f"actions/macro_{action_id}/version_1.json" in archive_entries
        assert f"actions/macro_{action_id}/version_2.json" in archive_entries

    with build_test_client(target_dir, monkeypatch) as target_client:
        import_response = target_client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "recording-bundle.zip",
                    export_response.content,
                    "application/zip",
                )
            },
        )

        assert import_response.status_code == 201
        payload = import_response.json()
        assert payload["actionIds"] == [action_id]

        imported_execution = target_client.get(f"/api/executions/{execution_id}")
        assert imported_execution.status_code == 200
        assert imported_execution.json()["actionVersion"] == 1

        imported_action = target_client.get(f"/api/actions/{action_id}")
        assert imported_action.status_code == 200
        assert imported_action.json()["version"] == 2

        assert (target_dir / f"actions/macro_{action_id}/version_1.json").exists()
        assert (target_dir / f"actions/macro_{action_id}/version_2.json").exists()


def test_importexport_rolls_back_partial_import_when_persistence_fails(
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source-data"
    target_dir = tmp_path / "target-data"

    with build_test_client(source_dir, monkeypatch) as source_client:
        recording_id, session_id = create_reviewed_recording(source_client)

        action_response = source_client.post("/api/actions", json={"recordingId": recording_id})
        assert action_response.status_code == 201
        action_id = action_response.json()["id"]

        execution_response = source_client.post(
            f"/api/actions/{action_id}/executions",
            json={
                "browserSessionId": session_id,
                "parameters": {
                    "amount": "208",
                    "currency": "USD",
                },
            },
        )
        assert execution_response.status_code == 201
        execution_id = execution_response.json()["id"]
        wait_for_terminal_execution(source_client, execution_id)

        detail_response = source_client.get(f"/api/recordings/{recording_id}")
        assert detail_response.status_code == 200
        request_body_blob_key = detail_response.json()["requests"][0]["requestBodyBlobKey"]

        export_response = source_client.get(f"/api/importexport/recordings/{recording_id}/bundle")
        assert export_response.status_code == 200

    with build_test_client(target_dir, monkeypatch) as target_client:
        service = target_client.app.state.importexport_import_service

        def fail_execution_save(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
            raise RuntimeError("simulated execution persistence failure")

        monkeypatch.setattr(
            target_client.app.state.execution_repository,
            "save",
            fail_execution_save,
        )

        with pytest.raises(RuntimeError, match="simulated execution persistence failure"):
            service.import_recording_bundle(export_response.content)

        assert target_client.get(f"/api/recordings/{recording_id}").status_code == 404
        assert target_client.get(f"/api/actions/{action_id}").status_code == 404
        assert target_client.get(f"/api/executions/{execution_id}").status_code == 404
        sessions_response = target_client.get("/api/sessions")
        assert sessions_response.status_code == 200
        assert sessions_response.json()["items"] == []

        assert not (target_dir / request_body_blob_key).exists()
        assert not (target_dir / f"actions/macro_{action_id}/version_1.json").exists()
        assert not (target_dir / f"runs/run_{execution_id}/run.json").exists()
        assert not (target_dir / f"runs/run_{execution_id}/logs/step-logs.json").exists()


def test_importexport_rejects_bundle_without_manifest(
    tmp_path,
    monkeypatch,
) -> None:
    target_dir = tmp_path / "target-data"
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("notes.txt", "missing manifest")

    with build_test_client(target_dir, monkeypatch) as client:
        response = client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "broken-bundle.zip",
                    buffer.getvalue(),
                    "application/zip",
                )
            },
        )

        assert response.status_code == 400
        assert "manifest" in response.json()["detail"].lower()


def test_importexport_rejects_bundle_when_manifest_references_missing_action_payload(
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source-data"
    target_dir = tmp_path / "target-data"

    with build_test_client(source_dir, monkeypatch) as source_client:
        recording_id, _session_id = create_reviewed_recording(source_client)
        action_response = source_client.post("/api/actions", json={"recordingId": recording_id})
        assert action_response.status_code == 201
        action_id = action_response.json()["id"]

        bundle_response = source_client.get(f"/api/importexport/recordings/{recording_id}/bundle")
        assert bundle_response.status_code == 200
        bundle_bytes = bundle_response.content

    missing_action_path = f"actions/macro_{action_id}/version_1.json"
    broken_buffer = BytesIO()
    with ZipFile(BytesIO(bundle_bytes)) as archive:
        with ZipFile(broken_buffer, "w") as broken_archive:
            for entry in archive.namelist():
                if entry == missing_action_path:
                    continue
                broken_archive.writestr(entry, archive.read(entry))

    with build_test_client(target_dir, monkeypatch) as target_client:
        response = target_client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "recording-bundle.zip",
                    broken_buffer.getvalue(),
                    "application/zip",
                )
            },
        )

        assert response.status_code == 400
        assert missing_action_path in response.json()["detail"]


def test_importexport_rejects_bundle_when_execution_references_missing_action_version(
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source-data"
    target_dir = tmp_path / "target-data"

    with build_test_client(source_dir, monkeypatch) as source_client:
        recording_id, session_id = create_reviewed_recording(source_client)
        action_response = source_client.post("/api/actions", json={"recordingId": recording_id})
        assert action_response.status_code == 201
        action_id = action_response.json()["id"]

        execution_response = source_client.post(
            f"/api/actions/{action_id}/executions",
            json={
                "browserSessionId": session_id,
                "parameters": {
                    "amount": "208",
                    "currency": "USD",
                },
            },
        )
        assert execution_response.status_code == 201
        execution_id = execution_response.json()["id"]
        wait_for_terminal_execution(source_client, execution_id)

        bundle_response = source_client.get(f"/api/importexport/recordings/{recording_id}/bundle")
        assert bundle_response.status_code == 200
        bundle_bytes = bundle_response.content

    execution_path = f"runs/run_{execution_id}/run.json"
    broken_buffer = BytesIO()
    with ZipFile(BytesIO(bundle_bytes)) as archive:
        manifest_payload = json.loads(archive.read("manifest.json"))
        for item in manifest_payload["execution_run_refs"]:
            if item["execution_id"] == execution_id:
                item["action_version"] = 99

        execution_payload = json.loads(archive.read(execution_path))
        execution_payload["action_version"] = 99

        with ZipFile(broken_buffer, "w") as broken_archive:
            for entry in archive.namelist():
                if entry == "manifest.json":
                    broken_archive.writestr(
                        entry,
                        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
                    )
                    continue
                if entry == execution_path:
                    broken_archive.writestr(
                        entry,
                        json.dumps(execution_payload, ensure_ascii=False, indent=2),
                    )
                    continue
                broken_archive.writestr(entry, archive.read(entry))

    with build_test_client(target_dir, monkeypatch) as target_client:
        response = target_client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "recording-bundle.zip",
                    broken_buffer.getvalue(),
                    "application/zip",
                )
            },
        )

        assert response.status_code == 400
        assert "action macro" in response.json()["detail"].lower()


def test_importexport_rejects_bundle_when_recording_references_missing_blob_file(
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source-data"
    target_dir = tmp_path / "target-data"

    with build_test_client(source_dir, monkeypatch) as source_client:
        recording_id, _session_id = create_reviewed_recording(source_client)
        detail_response = source_client.get(f"/api/recordings/{recording_id}")
        assert detail_response.status_code == 200
        request_body_blob_key = detail_response.json()["requests"][0]["requestBodyBlobKey"]

        bundle_response = source_client.get(f"/api/importexport/recordings/{recording_id}/bundle")
        assert bundle_response.status_code == 200
        bundle_bytes = bundle_response.content

    broken_buffer = BytesIO()
    with ZipFile(BytesIO(bundle_bytes)) as archive:
        manifest_payload = json.loads(archive.read("manifest.json"))
        manifest_payload["bundle"]["file_manifest"] = [
            entry
            for entry in manifest_payload["bundle"]["file_manifest"]
            if entry != request_body_blob_key
        ]

        with ZipFile(broken_buffer, "w") as broken_archive:
            for entry in archive.namelist():
                if entry == "manifest.json":
                    broken_archive.writestr(
                        entry,
                        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
                    )
                    continue
                if entry == request_body_blob_key:
                    continue
                broken_archive.writestr(entry, archive.read(entry))

    with build_test_client(target_dir, monkeypatch) as target_client:
        response = target_client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "recording-bundle.zip",
                    broken_buffer.getvalue(),
                    "application/zip",
                )
            },
        )

        assert response.status_code == 400
        assert request_body_blob_key in response.json()["detail"]


def test_importexport_rejects_duplicate_recording_import(
    tmp_path,
    monkeypatch,
) -> None:
    source_dir = tmp_path / "source-data"
    target_dir = tmp_path / "target-data"

    with build_test_client(source_dir, monkeypatch) as source_client:
        recording_id, session_id = create_reviewed_recording(source_client)
        action_response = source_client.post("/api/actions", json={"recordingId": recording_id})
        assert action_response.status_code == 201
        action_id = action_response.json()["id"]

        execution_response = source_client.post(
            f"/api/actions/{action_id}/executions",
            json={
                "browserSessionId": session_id,
                "parameters": {
                    "amount": "208",
                    "currency": "USD",
                },
            },
        )
        assert execution_response.status_code == 201
        execution_id = execution_response.json()["id"]
        wait_for_terminal_execution(source_client, execution_id)

        bundle_response = source_client.get(f"/api/importexport/recordings/{recording_id}/bundle")
        assert bundle_response.status_code == 200
        bundle_bytes = bundle_response.content

    with build_test_client(target_dir, monkeypatch) as target_client:
        first_import = target_client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "recording-bundle.zip",
                    bundle_bytes,
                    "application/zip",
                )
            },
        )
        assert first_import.status_code == 201

        second_import = target_client.post(
            "/api/importexport/recordings/import",
            files={
                "file": (
                    "recording-bundle.zip",
                    bundle_bytes,
                    "application/zip",
                )
            },
        )

        assert second_import.status_code == 409
        assert "already exists" in second_import.json()["detail"].lower()

    get_settings.cache_clear()
