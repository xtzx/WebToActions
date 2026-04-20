from datetime import UTC, datetime
import warnings

import pytest
from pydantic import ValidationError

from app.action.domain.action_macro import ActionMacro
from app.action.domain.action_step import ActionStep
from app.action.domain.business_action import BusinessAction
from app.action.domain.parameter_definition import ParameterDefinition, ParameterKind
from app.evidence.domain.file_transfer_record import FileTransferDirection, FileTransferRecord
from app.evidence.domain.page_stage import PageStage
from app.evidence.domain.request_response_record import RequestResponseRecord
from app.evidence.domain.session_state_snapshot import SessionStateSnapshot
from app.execution.domain.execution_run import (
    ExecutableActionKind,
    ExecutionRun,
    ExecutionRunStatus,
)
from app.importexport.domain.export_bundle import (
    ExportBundle,
    ExportScope,
    VersionedArtifactReference,
)
from app.recording.domain.recording import Recording, RecordingStatus
from app.review.domain.metadata_draft import MetadataDraft
from app.review.domain.reviewed_metadata import ReviewedMetadata
from app.session.domain.browser_session import BrowserSession, BrowserSessionStatus


def test_browser_session_uses_available_defaults_and_returns_new_instances_for_transitions() -> None:
    session = BrowserSession(id="session-1", profile_id="profile-1")

    assert session.status == BrowserSessionStatus.AVAILABLE
    assert session.created_at <= session.last_activity_at <= datetime.now(UTC)

    relogin_required = session.require_relogin()

    assert relogin_required is not None
    assert session.status == BrowserSessionStatus.AVAILABLE
    assert relogin_required.status == BrowserSessionStatus.RELOGIN_REQUIRED

    restored = relogin_required.restore()

    assert restored is not None
    assert relogin_required.status == BrowserSessionStatus.RELOGIN_REQUIRED
    assert restored.status == BrowserSessionStatus.AVAILABLE


def _request_replay_step(step_id: str, title: str) -> ActionStep:
    return ActionStep(
        id=step_id,
        title=title,
        request_id=f"req-{step_id}",
        request_method="POST",
        request_url=f"https://example.com/{step_id}",
    )


def test_browser_session_is_frozen_and_rejects_restoring_from_expired_state() -> None:
    session = BrowserSession(id="session-1", profile_id="profile-1")
    expired = session.expire()

    assert expired is not None

    with pytest.raises((ValidationError, TypeError), match="frozen"):
        expired.status = BrowserSessionStatus.AVAILABLE

    with pytest.raises(ValueError, match="expired"):
        expired.restore()


def test_recording_defaults_to_created_and_returns_new_instances_for_lifecycle() -> None:
    recording = Recording(
        id="recording-1",
        name="Create reimbursement",
        start_url="https://example.com/reimbursements/new",
        browser_session_id="session-1",
    )

    assert recording.status == RecordingStatus.CREATED
    assert recording.started_at is None
    assert recording.ended_at is None

    started = recording.start()

    assert started is not None
    assert recording.status == RecordingStatus.CREATED
    assert started.status == RecordingStatus.RECORDING
    assert started.started_at is not None

    finished = started.finish()

    assert finished is not None
    assert started.status == RecordingStatus.RECORDING
    assert finished.status == RecordingStatus.PENDING_REVIEW
    assert finished.ended_at is not None

    macro_generated = finished.mark_macro_generated(action_macro_id="macro-1")

    assert macro_generated is not None
    assert finished.status == RecordingStatus.PENDING_REVIEW
    assert macro_generated.status == RecordingStatus.MACRO_GENERATED
    assert macro_generated.generated_action_macro_id == "macro-1"


def test_recording_is_frozen_and_rejects_invalid_transitions() -> None:
    recording = Recording(
        id="recording-1",
        name="Create reimbursement",
        start_url="https://example.com/reimbursements/new",
        browser_session_id="session-1",
    )

    with pytest.raises((ValidationError, TypeError), match="frozen"):
        recording.status = RecordingStatus.RECORDING

    with pytest.raises(ValueError, match="pending_review"):
        recording.mark_macro_generated(action_macro_id="macro-1")


def test_recording_rejects_inconsistent_state_shape() -> None:
    with pytest.raises(ValidationError, match="started_at"):
        Recording(
            id="recording-1",
            name="Create reimbursement",
            start_url="https://example.com/reimbursements/new",
            browser_session_id="session-1",
            status=RecordingStatus.RECORDING,
        )

    with pytest.raises(ValidationError, match="ended_at"):
        Recording(
            id="recording-1",
            name="Create reimbursement",
            start_url="https://example.com/reimbursements/new",
            browser_session_id="session-1",
            status=RecordingStatus.PENDING_REVIEW,
            started_at=datetime(2026, 4, 19, tzinfo=UTC),
        )


def test_execution_run_defaults_to_pending_and_returns_new_instances_for_outcomes() -> None:
    run = ExecutionRun(
        id="run-1",
        action_kind=ExecutableActionKind.ACTION_MACRO,
        action_id="macro-1",
        action_version=2,
        browser_session_id="session-1",
        parameters_snapshot={"invoiceNumber": "INV-001"},
    )

    assert run.status == ExecutionRunStatus.PENDING
    assert run.started_at is None
    assert run.ended_at is None

    running = run.start()

    assert running is not None
    assert run.status == ExecutionRunStatus.PENDING
    assert running.status == ExecutionRunStatus.RUNNING
    assert running.started_at is not None

    succeeded = running.succeed()

    assert succeeded is not None
    assert running.status == ExecutionRunStatus.RUNNING
    assert succeeded.status == ExecutionRunStatus.SUCCEEDED
    assert succeeded.ended_at is not None
    assert succeeded.failure_reason is None


def test_execution_run_is_frozen_and_rejects_leaving_terminal_state() -> None:
    run = ExecutionRun(
        id="run-1",
        action_kind=ExecutableActionKind.ACTION_MACRO,
        action_id="macro-1",
        action_version=1,
        browser_session_id="session-1",
    )
    failed = run.start()

    assert failed is not None

    terminal = failed.fail("network timeout")

    assert terminal is not None

    with pytest.raises((ValidationError, TypeError), match="frozen"):
        terminal.status = ExecutionRunStatus.RUNNING

    with pytest.raises(ValueError, match="terminal"):
        terminal.succeed()


def test_execution_run_rejects_inconsistent_state_shape() -> None:
    with pytest.raises(ValidationError, match="started_at"):
        ExecutionRun(
            id="run-1",
            action_kind=ExecutableActionKind.ACTION_MACRO,
            action_id="macro-1",
            action_version=1,
            browser_session_id="session-1",
            status=ExecutionRunStatus.RUNNING,
        )

    with pytest.raises(ValidationError, match="failure_reason"):
        ExecutionRun(
            id="run-1",
            action_kind=ExecutableActionKind.ACTION_MACRO,
            action_id="macro-1",
            action_version=1,
            browser_session_id="session-1",
            status=ExecutionRunStatus.FAILED,
            started_at=datetime(2026, 4, 19, tzinfo=UTC),
            ended_at=datetime(2026, 4, 19, 0, 1, tzinfo=UTC),
        )


def test_evidence_models_keep_lightweight_indexes_and_body_references() -> None:
    page_stage = PageStage(
        id="stage-1",
        recording_id="recording-1",
        url="https://example.com/list",
        name="list page",
        started_at=datetime(2026, 4, 19, tzinfo=UTC),
        related_request_ids=["request-1", "request-2"],
        observable_state={"spinner": "hidden"},
    )
    request_record = RequestResponseRecord(
        id="request-1",
        recording_id="recording-1",
        request_method="POST",
        request_url="https://example.com/api/items",
        requested_at=datetime(2026, 4, 19, tzinfo=UTC),
        request_headers=[
            {"name": "x-trace-id", "value": "trace-1"},
            {"name": "set-cookie", "value": "a=1"},
            {"name": "set-cookie", "value": "b=2"},
        ],
        request_body_blob_key="evidence/requests/request-1/body.bin",
        response_status=200,
        response_headers=[
            {"name": "set-cookie", "value": "c=3"},
            {"name": "set-cookie", "value": "d=4"},
        ],
        response_body_blob_key="evidence/responses/request-1/body.bin",
    )
    snapshot = SessionStateSnapshot(
        id="snapshot-1",
        recording_id="recording-1",
        browser_session_id="session-1",
        captured_at=datetime(2026, 4, 19, tzinfo=UTC),
        cookie_summary={"session": "masked"},
        storage_summary={"localStorage": {"theme": "dark"}},
    )
    transfer = FileTransferRecord(
        id="file-1",
        recording_id="recording-1",
        direction=FileTransferDirection.UPLOAD,
        file_name="invoice.pdf",
        occurred_at=datetime(2026, 4, 19, tzinfo=UTC),
    )

    assert page_stage.ended_at is None
    assert [header.value for header in request_record.request_headers if header.name == "set-cookie"] == [
        "a=1",
        "b=2",
    ]
    assert request_record.request_body_blob_key == "evidence/requests/request-1/body.bin"
    assert request_record.response_body_blob_key == "evidence/responses/request-1/body.bin"
    assert snapshot.cookie_summary == {"session": "masked"}
    assert transfer.related_request_id is None

    with pytest.raises(TypeError, match="frozen"):
        page_stage.related_request_ids.append("request-3")

    with pytest.raises(TypeError, match="frozen"):
        page_stage.observable_state["spinner"] = "visible"

    with pytest.raises(TypeError, match="frozen"):
        request_record.request_headers.append({"name": "x-extra", "value": "1"})

    with pytest.raises(TypeError, match="frozen"):
        snapshot.storage_summary["localStorage"]["theme"] = "light"

    with pytest.raises((ValidationError, TypeError), match="frozen"):
        transfer.notes = "updated"


def test_page_stage_rejects_backwards_end_time() -> None:
    with pytest.raises(ValidationError, match="ended_at"):
        PageStage(
            id="stage-1",
            recording_id="recording-1",
            url="https://example.com/list",
            name="list page",
            started_at=datetime(2026, 4, 19, 1, tzinfo=UTC),
            ended_at=datetime(2026, 4, 19, 0, tzinfo=UTC),
        )


def test_metadata_and_review_versions_keep_stable_ids_and_support_version_evolution() -> None:
    draft_v1 = MetadataDraft(id="draft-1", recording_id="recording-1", version=1)

    assert callable(getattr(draft_v1, "next_version", None))

    draft_v2 = draft_v1.next_version(candidate_request_ids=["request-1"])

    assert draft_v1.id == draft_v2.id == "draft-1"
    assert draft_v1.version == 1
    assert draft_v1.previous_version is None
    assert draft_v2.version == 2
    assert draft_v2.previous_version == 1
    assert draft_v2.candidate_request_ids == ["request-1"]
    assert draft_v2.generated_at >= draft_v1.generated_at

    with pytest.raises(TypeError, match="frozen"):
        draft_v2.candidate_request_ids.append("request-2")

    reviewed_v1 = ReviewedMetadata(
        id="review-1",
        recording_id="recording-1",
        version=1,
        reviewer="alice",
        source_draft_id=draft_v1.id,
        source_draft_version=draft_v1.version,
    )

    assert callable(getattr(reviewed_v1, "next_version", None))

    reviewed_v2 = reviewed_v1.next_version(
        reviewer="bob",
        source_draft_version=draft_v2.version,
        risk_flags=["manual review required"],
    )

    assert reviewed_v1.id == reviewed_v2.id == "review-1"
    assert reviewed_v2.version == 2
    assert reviewed_v2.previous_version == 1
    assert reviewed_v2.source_draft_id == draft_v2.id
    assert reviewed_v2.source_draft_version == 2
    assert reviewed_v2.risk_flags == ["manual review required"]
    assert reviewed_v2.reviewed_at >= reviewed_v1.reviewed_at

    with pytest.raises(TypeError, match="frozen"):
        reviewed_v2.risk_flags.append("unexpected")


def test_versioned_artifacts_reject_cross_aggregate_drift_during_next_version() -> None:
    draft_v1 = MetadataDraft(id="draft-1", recording_id="recording-1", version=1)

    with pytest.raises(ValueError, match="recording_id"):
        draft_v1.next_version(recording_id="recording-2")

    reviewed_v1 = ReviewedMetadata(
        id="review-1",
        recording_id="recording-1",
        version=1,
        reviewer="alice",
        source_draft_id="draft-1",
        source_draft_version=1,
    )

    with pytest.raises(ValueError, match="recording_id"):
        reviewed_v1.next_version(recording_id="recording-2")

    with pytest.raises(ValueError, match="source_draft_id"):
        reviewed_v1.next_version(source_draft_id="draft-2")

    macro_v1 = ActionMacro(
        id="macro-1",
        recording_id="recording-1",
        name="Create reimbursement",
        version=1,
        source_reviewed_metadata_id="review-1",
        source_reviewed_metadata_version=1,
        steps=[_request_replay_step("step-1", "submit form")],
    )

    with pytest.raises(ValueError, match="recording_id"):
        macro_v1.next_version(recording_id="recording-2")

    with pytest.raises(ValueError, match="source_reviewed_metadata_id"):
        macro_v1.next_version(source_reviewed_metadata_id="review-2")

    business_v1 = BusinessAction(
        id="business-1",
        name="Submit reimbursement",
        version=1,
        source_action_macro_id="macro-1",
        source_action_macro_version=1,
    )

    with pytest.raises(ValueError, match="source_action_macro_id"):
        business_v1.next_version(source_action_macro_id="macro-2")


def test_versioned_metadata_models_are_frozen_and_reject_broken_previous_versions() -> None:
    draft_v1 = MetadataDraft(id="draft-1", recording_id="recording-1", version=1)

    with pytest.raises((ValidationError, TypeError), match="frozen"):
        draft_v1.version = 2

    with pytest.raises(ValidationError, match="previous_version"):
        MetadataDraft(id="draft-1", recording_id="recording-1", version=2)

    with pytest.raises(ValidationError, match="previous_version"):
        ReviewedMetadata(
            id="review-1",
            recording_id="recording-1",
            version=2,
            reviewer="alice",
            source_draft_id="draft-1",
            source_draft_version=1,
        )


def test_action_models_share_action_kind_semantics_and_version_identity() -> None:
    parameter = ParameterDefinition(
        id="parameter-1",
        action_id="macro-1",
        owner_kind=ExecutableActionKind.ACTION_MACRO,
        name="invoice_number",
        parameter_kind=ParameterKind.STRING,
        injection_target="request.body.invoiceNumber",
    )

    assert parameter.model_dump().get("owner_kind") == ExecutableActionKind.ACTION_MACRO

    macro_v1 = ActionMacro(
        id="macro-1",
        recording_id="recording-1",
        name="Create reimbursement",
        version=1,
        source_reviewed_metadata_id="review-1",
        source_reviewed_metadata_version=1,
        steps=[
            _request_replay_step("step-1", "open form"),
            _request_replay_step("step-2", "submit form"),
        ],
        parameter_definitions=[parameter],
    )

    assert callable(getattr(macro_v1, "next_version", None))

    macro_v2 = macro_v1.next_version(
        steps=[
            _request_replay_step("step-1", "open form"),
            _request_replay_step("step-2", "submit form"),
            _request_replay_step("step-3", "confirm result"),
        ]
    )

    assert macro_v1.id == macro_v2.id == "macro-1"
    assert macro_v2.version == 2
    assert macro_v2.previous_version == 1
    assert macro_v2.created_at >= macro_v1.created_at

    with pytest.raises(TypeError, match="frozen"):
        macro_v2.steps.append(_request_replay_step("step-x", "mutated"))

    business_parameter = ParameterDefinition(
        id="parameter-2",
        action_id="business-1",
        owner_kind=ExecutableActionKind.BUSINESS_ACTION,
        name="invoice_number",
        parameter_kind=ParameterKind.STRING,
        injection_target="input.invoiceNumber",
    )

    assert business_parameter.model_dump().get("owner_kind") == ExecutableActionKind.BUSINESS_ACTION

    business_v1 = BusinessAction(
        id="business-1",
        name="Submit reimbursement",
        version=1,
        source_action_macro_id=macro_v2.id,
        source_action_macro_version=macro_v2.version,
        parameter_definitions=[business_parameter],
    )

    assert callable(getattr(business_v1, "next_version", None))

    business_v2 = business_v1.next_version(outputs=["reimbursement_id"])

    assert business_v1.id == business_v2.id == "business-1"
    assert business_v2.version == 2
    assert business_v2.previous_version == 1
    assert business_v2.source_action_macro_id == macro_v2.id
    assert business_v2.source_action_macro_version == macro_v2.version
    assert business_v2.created_at >= business_v1.created_at

    with pytest.raises(TypeError, match="frozen"):
        business_v2.outputs.append("another-output")


def test_domain_models_serialize_plain_payloads_for_storage_boundaries() -> None:
    macro = ActionMacro(
        id="macro-1",
        recording_id="recording-1",
        name="Create reimbursement",
        version=1,
        source_reviewed_metadata_id="review-1",
        source_reviewed_metadata_version=1,
        steps=[_request_replay_step("step-1", "open form")],
        parameter_definitions=[
            ParameterDefinition(
                id="parameter-1",
                action_id="macro-1",
                owner_kind=ExecutableActionKind.ACTION_MACRO,
                name="invoice_number",
                parameter_kind=ParameterKind.STRING,
                injection_target="request.body.invoiceNumber",
            )
        ],
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        payload = macro.model_dump()

    assert caught == []
    assert payload["steps"][0]["title"] == "open form"
    assert payload["parameter_definitions"][0]["owner_kind"] == ExecutableActionKind.ACTION_MACRO
    assert "steps" not in macro.model_dump(exclude={"steps"})
    assert macro.model_dump(include={"id"}) == {"id": "macro-1"}
    assert "description" not in macro.model_dump(exclude_none=True)
    assert '"title":"open form"' in macro.model_dump_json()


def test_action_models_are_frozen_and_reject_owner_kind_or_previous_version_mismatches() -> None:
    macro_parameter = ParameterDefinition(
        id="parameter-1",
        action_id="macro-1",
        owner_kind=ExecutableActionKind.ACTION_MACRO,
        name="invoice_number",
        parameter_kind=ParameterKind.STRING,
        injection_target="request.body.invoiceNumber",
    )
    macro_v1 = ActionMacro(
        id="macro-1",
        recording_id="recording-1",
        name="Create reimbursement",
        version=1,
        source_reviewed_metadata_id="review-1",
        source_reviewed_metadata_version=1,
        steps=[_request_replay_step("step-1", "submit form")],
        parameter_definitions=[macro_parameter],
    )

    with pytest.raises((ValidationError, TypeError), match="frozen"):
        macro_v1.version = 2

    with pytest.raises(ValidationError, match="owner_kind"):
        ActionMacro(
            id="macro-1",
            recording_id="recording-1",
            name="Create reimbursement",
            version=1,
            source_reviewed_metadata_id="review-1",
            source_reviewed_metadata_version=1,
            steps=[_request_replay_step("step-1", "submit form")],
            parameter_definitions=[
                ParameterDefinition(
                    id="parameter-2",
                    action_id="macro-1",
                    owner_kind=ExecutableActionKind.BUSINESS_ACTION,
                    name="invoice_number",
                    parameter_kind=ParameterKind.STRING,
                    injection_target="request.body.invoiceNumber",
                )
            ],
        )

    with pytest.raises(ValidationError, match="previous_version"):
        ActionMacro(
            id="macro-1",
            recording_id="recording-1",
            name="Create reimbursement",
            version=2,
            source_reviewed_metadata_id="review-1",
            source_reviewed_metadata_version=1,
            steps=[_request_replay_step("step-1", "submit form")],
        )

    with pytest.raises(ValidationError, match="previous_version"):
        BusinessAction(
            id="business-1",
            name="Submit reimbursement",
            version=2,
            source_action_macro_id="macro-1",
            source_action_macro_version=1,
        )


def test_export_bundle_keeps_versioned_members_aligned_with_execution_targets() -> None:
    run = ExecutionRun(
        id="run-1",
        action_kind=ExecutableActionKind.BUSINESS_ACTION,
        action_id="business-1",
        action_version=2,
        browser_session_id="session-1",
    )
    reviewed_ref = VersionedArtifactReference(artifact_id="review-1", version=2)
    macro_ref = VersionedArtifactReference(artifact_id="macro-1", version=2)
    business_ref = VersionedArtifactReference(
        artifact_id=run.action_id,
        version=run.action_version,
    )

    bundle_v1 = ExportBundle(
        id="bundle-1",
        version=1,
        export_scope=ExportScope.RECORDING,
        package_format_version="1.0",
        recording_ids=["recording-1"],
        reviewed_metadata_refs=[reviewed_ref],
        action_macro_refs=[macro_ref],
        business_action_refs=[business_ref],
        file_manifest=["manifest.json"],
    )

    assert callable(getattr(bundle_v1, "next_version", None))

    bundle_v2 = bundle_v1.next_version(file_manifest=["manifest.json", "bundle-v2.json"])

    assert bundle_v1.id == bundle_v2.id == "bundle-1"
    assert bundle_v2.version == 2
    assert bundle_v2.previous_version == 1
    assert bundle_v2.package_format_version == "1.0"
    assert bundle_v2.exported_at >= bundle_v1.exported_at
    assert bundle_v2.reviewed_metadata_refs[0].artifact_id == "review-1"
    assert bundle_v2.action_macro_refs[0].artifact_id == "macro-1"
    assert bundle_v2.business_action_refs[0].artifact_id == run.action_id
    assert bundle_v2.business_action_refs[0].version == run.action_version

    with pytest.raises(TypeError, match="frozen"):
        bundle_v2.file_manifest.append("mutated")


def test_export_bundle_rejects_invalid_versioned_references() -> None:
    with pytest.raises(ValidationError, match="version"):
        VersionedArtifactReference(artifact_id="review-1", version=0)

    with pytest.raises(ValidationError, match="previous_version"):
        ExportBundle(
            id="bundle-1",
            version=2,
            export_scope=ExportScope.RECORDING,
            package_format_version="1.0",
        )
