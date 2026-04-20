from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

from app.action.domain import ActionMacro
from app.evidence.domain import (
    FileTransferRecord,
    PageStage,
    RequestResponseRecord,
    SessionStateSnapshot,
)
from app.execution.domain.execution_run import ExecutionRun
from app.recording.repository import RecordingAggregate
from app.recording.domain.recording import Recording
from app.review.domain.metadata_draft import MetadataDraft
from app.review.domain.reviewed_metadata import ReviewedMetadata
from app.session.domain.browser_session import BrowserSession

RECORDING_AGGREGATE_PATH = "recording-aggregate.json"


def serialize_recording_aggregate(aggregate: RecordingAggregate) -> dict[str, Any]:
    return {
        "recording": aggregate.recording.model_dump(mode="json"),
        "browserSession": (
            aggregate.browser_session.model_dump(mode="json")
            if aggregate.browser_session is not None
            else None
        ),
        "pageStages": [item.model_dump(mode="json") for item in aggregate.page_stages],
        "requestResponseRecords": [
            item.model_dump(mode="json") for item in aggregate.request_response_records
        ],
        "sessionStateSnapshots": [
            item.model_dump(mode="json") for item in aggregate.session_state_snapshots
        ],
        "fileTransferRecords": [
            item.model_dump(mode="json") for item in aggregate.file_transfer_records
        ],
        "metadataDrafts": [item.model_dump(mode="json") for item in aggregate.metadata_drafts],
        "reviewedMetadata": [
            item.model_dump(mode="json") for item in aggregate.reviewed_metadata
        ],
    }


def deserialize_recording_aggregate(payload: dict[str, Any]) -> RecordingAggregate:
    browser_session_payload = payload.get("browserSession")
    return RecordingAggregate(
        recording=Recording.model_validate(payload["recording"]),
        browser_session=(
            BrowserSession.model_validate(browser_session_payload)
            if browser_session_payload is not None
            else None
        ),
        page_stages=tuple(
            PageStage.model_validate(item) for item in payload.get("pageStages", [])
        ),
        request_response_records=tuple(
            RequestResponseRecord.model_validate(item)
            for item in payload.get("requestResponseRecords", [])
        ),
        session_state_snapshots=tuple(
            SessionStateSnapshot.model_validate(item)
            for item in payload.get("sessionStateSnapshots", [])
        ),
        file_transfer_records=tuple(
            FileTransferRecord.model_validate(item)
            for item in payload.get("fileTransferRecords", [])
        ),
        metadata_drafts=tuple(
            MetadataDraft.model_validate(item)
            for item in payload.get("metadataDrafts", [])
        ),
        reviewed_metadata=tuple(
            ReviewedMetadata.model_validate(item)
            for item in payload.get("reviewedMetadata", [])
        ),
    )


def deserialize_action_macro(payload: dict[str, Any]) -> ActionMacro:
    return ActionMacro.model_validate(payload)


def deserialize_execution_run(payload: dict[str, Any]) -> ExecutionRun:
    return ExecutionRun.model_validate(payload)


def ensure_safe_archive_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value.strip() or path.is_absolute() or ".." in path.parts:
        raise ValueError("Archive contains an unsafe file path.")
    return path
