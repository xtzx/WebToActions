from dataclasses import dataclass
from typing import Protocol

from app.evidence.domain import (
    FileTransferRecord,
    PageStage,
    RequestResponseRecord,
    SessionStateSnapshot,
)
from app.recording.domain.recording import Recording
from app.review.domain.metadata_draft import MetadataDraft
from app.review.domain.reviewed_metadata import ReviewedMetadata
from app.session.domain.browser_session import BrowserSession


@dataclass(frozen=True, kw_only=True)
class RecordingAggregate:
    recording: Recording
    browser_session: BrowserSession | None = None
    page_stages: tuple[PageStage, ...] = ()
    request_response_records: tuple[RequestResponseRecord, ...] = ()
    session_state_snapshots: tuple[SessionStateSnapshot, ...] = ()
    file_transfer_records: tuple[FileTransferRecord, ...] = ()
    metadata_drafts: tuple[MetadataDraft, ...] = ()
    reviewed_metadata: tuple[ReviewedMetadata, ...] = ()


class RecordingRepository(Protocol):
    def save(self, aggregate: RecordingAggregate) -> None:
        """Persist one recording aggregate."""

    def get(self, recording_id: str) -> RecordingAggregate | None:
        """Load one recording aggregate by recording id."""

    def list(self) -> tuple[RecordingAggregate, ...]:
        """List persisted recording aggregates."""
