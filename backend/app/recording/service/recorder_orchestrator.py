from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from queue import Empty, Queue
from threading import Lock
from typing import Any
from uuid import uuid4

from app.browser.playwright_bridge import (
    BrowserBridge,
    BrowserRecordingHandle,
    RecordingCallbacks,
)
from app.evidence.service.evidence_writer import EvidenceWriter
from app.evidence.service.file_transfer_collector import FileTransferCollector
from app.evidence.service.network_collector import NetworkCollector
from app.evidence.service.page_stage_tracker import PageStageTracker
from app.evidence.service.session_state_collector import SessionStateCollector
from app.recording.domain.recording import Recording
from app.recording.repository import RecordingAggregate, RecordingRepository
from app.session.domain.browser_session import BrowserSession
from app.session.service.browser_session_manager import BrowserSessionManager


@dataclass
class _ActiveRecordingRuntime:
    recording: Recording
    browser_session: BrowserSession
    handle: BrowserRecordingHandle
    page_stage_tracker: PageStageTracker
    network_collector: NetworkCollector
    file_transfer_collector: FileTransferCollector


class RecordingEventBroker:
    def __init__(self) -> None:
        self._lock = Lock()
        self._latest: dict[str, dict[str, Any]] = {}
        self._subscribers: dict[str, list[Queue[dict[str, Any]]]] = {}

    def publish(self, recording_id: str, snapshot: dict[str, Any]) -> None:
        with self._lock:
            self._latest[recording_id] = snapshot
            subscribers = list(self._subscribers.get(recording_id, []))
        for queue in subscribers:
            queue.put(snapshot)

    def subscribe(self, recording_id: str) -> tuple[dict[str, Any] | None, Queue[dict[str, Any]]]:
        queue: Queue[dict[str, Any]] = Queue()
        with self._lock:
            self._subscribers.setdefault(recording_id, []).append(queue)
            latest = self._latest.get(recording_id)
        return latest, queue

    def unsubscribe(self, recording_id: str, queue: Queue[dict[str, Any]]) -> None:
        with self._lock:
            subscribers = self._subscribers.get(recording_id)
            if subscribers is None:
                return
            self._subscribers[recording_id] = [
                item for item in subscribers if item is not queue
            ]
            if not self._subscribers[recording_id]:
                self._subscribers.pop(recording_id, None)


class RecorderOrchestrator:
    def __init__(
        self,
        *,
        browser_bridge: BrowserBridge,
        session_manager: BrowserSessionManager,
        recording_repository: RecordingRepository,
        evidence_writer: EvidenceWriter,
        session_state_collector: SessionStateCollector,
        event_broker: RecordingEventBroker,
    ) -> None:
        self._browser_bridge = browser_bridge
        self._session_manager = session_manager
        self._recording_repository = recording_repository
        self._evidence_writer = evidence_writer
        self._session_state_collector = session_state_collector
        self._event_broker = event_broker
        self._active_recordings: dict[str, _ActiveRecordingRuntime] = {}

    def list_recordings(self) -> tuple[RecordingAggregate, ...]:
        persisted = {item.recording.id: item for item in self._recording_repository.list()}
        for recording_id, runtime in self._active_recordings.items():
            persisted[recording_id] = self._active_aggregate(runtime)
        return tuple(
            sorted(
                persisted.values(),
                key=lambda item: item.recording.created_at,
                reverse=True,
            )
        )

    def get_recording(self, recording_id: str) -> RecordingAggregate | None:
        runtime = self._active_recordings.get(recording_id)
        if runtime is not None:
            return self._active_aggregate(runtime)
        return self._recording_repository.get(recording_id)

    def start_recording(
        self,
        *,
        name: str,
        start_url: str,
        browser_session_id: str | None,
    ) -> RecordingAggregate:
        browser_session = self._session_manager.ensure_session(browser_session_id)
        recording = Recording(
            id=f"recording-{uuid4().hex[:8]}",
            name=name,
            start_url=start_url,
            browser_session_id=browser_session.id,
        ).start()
        page_stage_tracker = PageStageTracker(recording_id=recording.id)
        network_collector = NetworkCollector(
            recording_id=recording.id,
            page_stage_tracker=page_stage_tracker,
        )
        file_transfer_collector = FileTransferCollector(recording_id=recording.id)

        def publish(status: str) -> None:
            self._event_broker.publish(
                recording.id,
                _build_snapshot(
                    recording_id=recording.id,
                    status=status,
                    current_url=page_stage_tracker.current_url(),
                    request_count=network_collector.count(),
                    page_stage_count=page_stage_tracker.count(),
                    file_transfer_count=file_transfer_collector.count(),
                ),
            )

        callbacks = _RecordingCallbacksAdapter(
            page_stage_tracker=page_stage_tracker,
            network_collector=network_collector,
            file_transfer_collector=file_transfer_collector,
            publisher=lambda: publish(recording.status.value),
        )
        handle = self._browser_bridge.start_recording(
            profile_dir=self._session_manager.profile_dir(browser_session.profile_id),
            start_url=start_url,
            callbacks=callbacks,
        )
        runtime = _ActiveRecordingRuntime(
            recording=recording,
            browser_session=browser_session,
            handle=handle,
            page_stage_tracker=page_stage_tracker,
            network_collector=network_collector,
            file_transfer_collector=file_transfer_collector,
        )
        self._active_recordings[recording.id] = runtime
        self._recording_repository.save(
            RecordingAggregate(
                recording=recording,
                browser_session=browser_session,
            )
        )
        publish(recording.status.value)
        return self._active_aggregate(runtime)

    def stop_recording(self, recording_id: str) -> RecordingAggregate:
        runtime = self._active_recordings.pop(recording_id, None)
        if runtime is None:
            raise KeyError(f"Recording {recording_id} is not active.")

        browser_snapshot = runtime.handle.stop()
        runtime.page_stage_tracker.finish()
        finished_recording = runtime.recording.finish()
        updated_session = self._session_manager.update_session_activity(
            runtime.browser_session,
            login_site_summaries=list(browser_snapshot.get("loginSiteSummaries", [])),
        )
        snapshot = self._session_state_collector.build_snapshot(
            recording_id=finished_recording.id,
            browser_session_id=updated_session.id,
            page_stage_id=(
                runtime.page_stage_tracker.current_stage().id
                if runtime.page_stage_tracker.current_stage() is not None
                else None
            ),
            snapshot_id="snapshot-1",
            browser_snapshot=browser_snapshot,
            evidence_writer=self._evidence_writer,
        )
        aggregate = RecordingAggregate(
            recording=finished_recording,
            browser_session=updated_session,
            page_stages=runtime.page_stage_tracker.snapshot(),
            request_response_records=runtime.network_collector.export(
                evidence_writer=self._evidence_writer
            ),
            session_state_snapshots=(snapshot,),
            file_transfer_records=runtime.file_transfer_collector.snapshot(),
        )
        self._recording_repository.save(aggregate)
        self._event_broker.publish(
            recording_id,
            _build_snapshot(
                recording_id=recording_id,
                status=finished_recording.status.value,
                current_url=str(browser_snapshot.get("currentUrl") or ""),
                request_count=len(aggregate.request_response_records),
                page_stage_count=len(aggregate.page_stages),
                file_transfer_count=len(aggregate.file_transfer_records),
            ),
        )
        return aggregate

    def subscribe_events(
        self,
        recording_id: str,
    ) -> tuple[dict[str, Any] | None, Queue[dict[str, Any]]]:
        return self._event_broker.subscribe(recording_id)

    def unsubscribe_events(self, recording_id: str, queue: Queue[dict[str, Any]]) -> None:
        self._event_broker.unsubscribe(recording_id, queue)

    def wait_for_event(
        self,
        queue: Queue[dict[str, Any]],
        *,
        timeout_seconds: float,
    ) -> dict[str, Any] | None:
        try:
            return queue.get(timeout=timeout_seconds)
        except Empty:
            return None

    def _active_aggregate(self, runtime: _ActiveRecordingRuntime) -> RecordingAggregate:
        return RecordingAggregate(
            recording=runtime.recording,
            browser_session=runtime.browser_session,
            page_stages=runtime.page_stage_tracker.snapshot(),
            request_response_records=runtime.network_collector.snapshot(),
            file_transfer_records=runtime.file_transfer_collector.snapshot(),
        )


class _RecordingCallbacksAdapter:
    def __init__(
        self,
        *,
        page_stage_tracker: PageStageTracker,
        network_collector: NetworkCollector,
        file_transfer_collector: FileTransferCollector,
        publisher,
    ) -> None:
        self._page_stage_tracker = page_stage_tracker
        self._network_collector = network_collector
        self._file_transfer_collector = file_transfer_collector
        self._publisher = publisher

    def on_navigation(self, *, url: str, title: str | None) -> None:
        self._page_stage_tracker.on_navigation(url=url, title=title)
        self._publisher()

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
    ) -> None:
        self._network_collector.on_request(
            request_id=request_id,
            method=method,
            url=url,
            headers=headers,
            body=body,
            resource_type=resource_type,
            is_navigation_request=is_navigation_request,
        )
        self._publisher()

    def on_response(
        self,
        *,
        request_id: str,
        status: int,
        status_text: str,
        headers: list[tuple[str, str]],
        body: bytes | None,
    ) -> None:
        self._network_collector.on_response(
            request_id=request_id,
            status=status,
            status_text=status_text,
            headers=headers,
            body=body,
        )
        self._publisher()

    def on_request_failed(self, *, request_id: str, reason: str) -> None:
        self._network_collector.on_request_failed(request_id=request_id, reason=reason)
        self._publisher()

    def on_upload(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None:
        self._file_transfer_collector.on_upload(
            transfer_id=transfer_id,
            file_name=file_name,
            related_request_id=related_request_id,
        )
        self._publisher()

    def on_download(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None:
        self._file_transfer_collector.on_download(
            transfer_id=transfer_id,
            file_name=file_name,
            related_request_id=related_request_id,
        )
        self._publisher()


def _build_snapshot(
    *,
    recording_id: str,
    status: str,
    current_url: str | None,
    request_count: int,
    page_stage_count: int,
    file_transfer_count: int,
) -> dict[str, Any]:
    return {
        "recordingId": recording_id,
        "status": status,
        "currentUrl": current_url or "",
        "requestCount": request_count,
        "pageStageCount": page_stage_count,
        "fileTransferCount": file_transfer_count,
        "updatedAt": datetime.now(UTC).isoformat(),
    }
