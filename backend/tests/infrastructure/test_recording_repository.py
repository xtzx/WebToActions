from datetime import UTC, datetime
from pathlib import Path

from app.infrastructure.db.recording_repository import SqliteRecordingRepository
from app.infrastructure.db.runtime import initialize_sqlite_runtime
from app.infrastructure.storage.storage_bootstrap import bootstrap_storage_layout
from app.recording.domain.recording import Recording
from app.recording.repository import RecordingAggregate
from app.review.domain.metadata_draft import MetadataDraft
from app.review.domain.reviewed_metadata import ReviewedMetadata
from app.session.domain.browser_session import BrowserSession


def test_sqlite_recording_repository_round_trips_recording_and_related_metadata(
    tmp_path: Path,
) -> None:
    layout = bootstrap_storage_layout(tmp_path / ".webtoactions")
    runtime = initialize_sqlite_runtime(layout.database_path)
    repository = SqliteRecordingRepository(runtime.session_factory)

    aggregate = RecordingAggregate(
        browser_session=BrowserSession(id="session-1", profile_id="profile-1"),
        recording=Recording(
            id="recording-1",
            name="Create reimbursement",
            start_url="https://example.com/reimbursements/new",
            browser_session_id="session-1",
        ),
        metadata_drafts=(
            MetadataDraft(
                id="draft-1",
                recording_id="recording-1",
                version=1,
                candidate_request_ids=["request-1"],
            ),
        ),
        reviewed_metadata=(
            ReviewedMetadata(
                id="review-1",
                recording_id="recording-1",
                version=1,
                reviewer="alice",
                source_draft_id="draft-1",
                source_draft_version=1,
                reviewed_at=datetime(2026, 4, 19, tzinfo=UTC),
            ),
        ),
    )

    repository.save(aggregate)
    loaded = repository.get("recording-1")

    assert loaded == aggregate
