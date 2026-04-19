from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any

from app.recording.domain.recording import RecordingStatus
from app.recording.repository import RecordingRepository
from app.review.service.metadata_analysis_service import MetadataAnalysisService


@dataclass(frozen=True)
class ReviewJobSnapshot:
    recording_id: str
    status: str
    latest_draft_version: int | None
    error: str | None
    updated_at: str


class ReviewAnalysisUnavailableError(ValueError):
    """Raised when a recording is not ready for metadata analysis."""


class ReviewJobRunner:
    def __init__(
        self,
        *,
        metadata_analysis_service: MetadataAnalysisService,
        recording_repository: RecordingRepository,
    ) -> None:
        self._metadata_analysis_service = metadata_analysis_service
        self._recording_repository = recording_repository
        self._lock = Lock()
        self._active_recordings: set[str] = set()
        self._snapshots: dict[str, ReviewJobSnapshot] = {}
        self._subscribers: dict[str, list[Queue[ReviewJobSnapshot]]] = {}

    def ensure_started(self, recording_id: str) -> ReviewJobSnapshot:
        aggregate = self._recording_repository.get(recording_id)
        if aggregate is None:
            raise KeyError(f"Recording {recording_id} not found.")

        latest_draft = aggregate.metadata_drafts[-1] if aggregate.metadata_drafts else None
        if latest_draft is not None:
            snapshot = ReviewJobSnapshot(
                recording_id=recording_id,
                status="completed",
                latest_draft_version=latest_draft.version,
                error=None,
                updated_at=_utc_now(),
            )
            self._publish(snapshot)
            return snapshot

        if aggregate.recording.status not in {
            RecordingStatus.PENDING_REVIEW,
            RecordingStatus.MACRO_GENERATED,
        }:
            raise ReviewAnalysisUnavailableError(
                "Review analysis is only available after recording has finished."
            )

        with self._lock:
            existing = self._snapshots.get(recording_id)
            if recording_id in self._active_recordings and existing is not None:
                return existing
            self._active_recordings.add(recording_id)

        queued = ReviewJobSnapshot(
            recording_id=recording_id,
            status="queued",
            latest_draft_version=None,
            error=None,
            updated_at=_utc_now(),
        )
        self._publish(queued)
        thread = Thread(
            target=self._run_job,
            kwargs={"recording_id": recording_id},
            daemon=True,
        )
        thread.start()
        return queued

    def get_snapshot(self, recording_id: str) -> ReviewJobSnapshot | None:
        aggregate = self._recording_repository.get(recording_id)
        if aggregate is None:
            return None
        latest_draft = aggregate.metadata_drafts[-1] if aggregate.metadata_drafts else None
        if latest_draft is not None:
            return ReviewJobSnapshot(
                recording_id=recording_id,
                status="completed",
                latest_draft_version=latest_draft.version,
                error=None,
                updated_at=_utc_now(),
            )
        return self._snapshots.get(recording_id)

    def subscribe(
        self,
        recording_id: str,
    ) -> tuple[ReviewJobSnapshot | None, Queue[ReviewJobSnapshot]]:
        queue: Queue[ReviewJobSnapshot] = Queue()
        with self._lock:
            self._subscribers.setdefault(recording_id, []).append(queue)
            latest = self._snapshots.get(recording_id)
        if latest is None:
            latest = self.get_snapshot(recording_id)
        return latest, queue

    def unsubscribe(
        self,
        recording_id: str,
        queue: Queue[ReviewJobSnapshot],
    ) -> None:
        with self._lock:
            subscribers = self._subscribers.get(recording_id)
            if subscribers is None:
                return
            self._subscribers[recording_id] = [
                item for item in subscribers if item is not queue
            ]
            if not self._subscribers[recording_id]:
                self._subscribers.pop(recording_id, None)

    def wait_for_event(
        self,
        queue: Queue[ReviewJobSnapshot],
        *,
        timeout_seconds: float,
    ) -> ReviewJobSnapshot | None:
        try:
            return queue.get(timeout=timeout_seconds)
        except Empty:
            return None

    def _run_job(self, *, recording_id: str) -> None:
        self._publish(
            ReviewJobSnapshot(
                recording_id=recording_id,
                status="running",
                latest_draft_version=None,
                error=None,
                updated_at=_utc_now(),
            )
        )
        try:
            draft = self._metadata_analysis_service.analyze_recording(recording_id)
        except Exception as exc:
            self._publish(
                ReviewJobSnapshot(
                    recording_id=recording_id,
                    status="failed",
                    latest_draft_version=None,
                    error=str(exc),
                    updated_at=_utc_now(),
                )
            )
        else:
            self._publish(
                ReviewJobSnapshot(
                    recording_id=recording_id,
                    status="completed",
                    latest_draft_version=draft.version,
                    error=None,
                    updated_at=_utc_now(),
                )
            )
        finally:
            with self._lock:
                self._active_recordings.discard(recording_id)

    def _publish(self, snapshot: ReviewJobSnapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.recording_id] = snapshot
            subscribers = list(self._subscribers.get(snapshot.recording_id, []))
        for queue in subscribers:
            queue.put(snapshot)


def serialize_review_snapshot(snapshot: ReviewJobSnapshot) -> dict[str, Any]:
    return {
        "recordingId": snapshot.recording_id,
        "status": snapshot.status,
        "latestDraftVersion": snapshot.latest_draft_version,
        "error": snapshot.error,
        "updatedAt": snapshot.updated_at,
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
