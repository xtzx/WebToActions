from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.recording.repository import RecordingAggregate

router = APIRouter(prefix="/recordings", tags=["recordings"])


class CreateRecordingRequest(BaseModel):
    name: str = Field(min_length=1)
    start_url: str = Field(alias="startUrl", min_length=1)
    browser_session_id: str | None = Field(default=None, alias="browserSessionId")

    model_config = {"populate_by_name": True}


@router.get("")
def list_recordings(request: Request) -> dict[str, list[dict[str, object]]]:
    orchestrator = request.app.state.recorder_orchestrator
    items = orchestrator.list_recordings()
    return {"items": [_serialize_recording_summary(item) for item in items]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_recording(
    payload: CreateRecordingRequest,
    request: Request,
) -> dict[str, object]:
    orchestrator = request.app.state.recorder_orchestrator
    try:
        aggregate = orchestrator.start_recording(
            name=payload.name,
            start_url=payload.start_url,
            browser_session_id=payload.browser_session_id,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_recording_summary(aggregate)


@router.get("/{recording_id}")
def get_recording_detail(recording_id: str, request: Request) -> dict[str, object]:
    orchestrator = request.app.state.recorder_orchestrator
    aggregate = orchestrator.get_recording(recording_id)
    if aggregate is None:
        raise HTTPException(status_code=404, detail="Recording not found.")
    return _serialize_recording_detail(aggregate)


@router.post("/{recording_id}/stop")
def stop_recording(recording_id: str, request: Request) -> dict[str, object]:
    orchestrator = request.app.state.recorder_orchestrator
    try:
        aggregate = orchestrator.stop_recording(recording_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    review_job_runner = getattr(request.app.state, "review_job_runner", None)
    if review_job_runner is not None:
        review_job_runner.ensure_started(recording_id)
    return _serialize_recording_detail(aggregate)


@router.get("/{recording_id}/events")
def stream_recording_events(
    recording_id: str,
    request: Request,
    once: bool = False,
) -> StreamingResponse:
    orchestrator = request.app.state.recorder_orchestrator
    aggregate = orchestrator.get_recording(recording_id)
    if aggregate is None:
        raise HTTPException(status_code=404, detail="Recording not found.")

    latest, queue = orchestrator.subscribe_events(recording_id)

    async def event_stream():
        try:
            if latest is not None:
                yield _encode_sse(latest)
            if once:
                return
            while not await request.is_disconnected():
                snapshot = await asyncio.to_thread(
                    orchestrator.wait_for_event,
                    queue,
                    timeout_seconds=1.0,
                )
                if snapshot is None:
                    yield ": keep-alive\n\n"
                    continue
                yield _encode_sse(snapshot)
        finally:
            orchestrator.unsubscribe_events(recording_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


def _serialize_recording_summary(aggregate: RecordingAggregate) -> dict[str, object]:
    page_stages = aggregate.page_stages
    requests = aggregate.request_response_records
    file_transfers = aggregate.file_transfer_records
    current_url = page_stages[-1].url if page_stages else aggregate.recording.start_url
    return {
        "id": aggregate.recording.id,
        "name": aggregate.recording.name,
        "startUrl": aggregate.recording.start_url,
        "browserSessionId": aggregate.recording.browser_session_id,
        "status": aggregate.recording.status.value,
        "createdAt": aggregate.recording.created_at.isoformat(),
        "startedAt": (
            aggregate.recording.started_at.isoformat()
            if aggregate.recording.started_at is not None
            else None
        ),
        "endedAt": (
            aggregate.recording.ended_at.isoformat()
            if aggregate.recording.ended_at is not None
            else None
        ),
        "currentUrl": current_url,
        "requestCount": len(requests),
        "pageStageCount": len(page_stages),
        "fileTransferCount": len(file_transfers),
        "sessionSnapshotCount": len(aggregate.session_state_snapshots),
        "failedRequestCount": sum(
            1 for item in requests if item.failure_reason is not None
        ),
    }


def _serialize_recording_detail(aggregate: RecordingAggregate) -> dict[str, object]:
    payload = _serialize_recording_summary(aggregate)
    payload.update(
        {
            "pageStages": [
                {
                    "id": item.id,
                    "url": item.url,
                    "name": item.name,
                    "startedAt": item.started_at.isoformat(),
                    "endedAt": item.ended_at.isoformat() if item.ended_at else None,
                    "relatedRequestIds": list(item.related_request_ids),
                    "waitPoints": list(item.wait_points),
                    "observableState": dict(item.observable_state),
                }
                for item in aggregate.page_stages
            ],
            "requests": [
                {
                    "id": item.id,
                    "requestMethod": item.request_method,
                    "requestUrl": item.request_url,
                    "requestedAt": item.requested_at.isoformat(),
                    "requestHeaders": [
                        {"name": header.name, "value": header.value}
                        for header in item.request_headers
                    ],
                    "requestBodyBlobKey": item.request_body_blob_key,
                    "responseStatus": item.response_status,
                    "responseHeaders": [
                        {"name": header.name, "value": header.value}
                        for header in item.response_headers
                    ],
                    "responseBodyBlobKey": item.response_body_blob_key,
                    "finishedAt": item.finished_at.isoformat() if item.finished_at else None,
                    "durationMs": item.duration_ms,
                    "pageStageId": item.page_stage_id,
                    "failureReason": item.failure_reason,
                }
                for item in aggregate.request_response_records
            ],
            "sessionSnapshots": [
                {
                    "id": item.id,
                    "browserSessionId": item.browser_session_id,
                    "capturedAt": item.captured_at.isoformat(),
                    "pageStageId": item.page_stage_id,
                    "requestId": item.request_id,
                    "cookieSummary": dict(item.cookie_summary),
                    "storageSummary": {
                        key: dict(value) for key, value in item.storage_summary.items()
                    },
                }
                for item in aggregate.session_state_snapshots
            ],
            "fileTransfers": [
                {
                    "id": item.id,
                    "direction": item.direction.value,
                    "fileName": item.file_name,
                    "occurredAt": item.occurred_at.isoformat(),
                    "relatedRequestId": item.related_request_id,
                    "sourcePathSummary": item.source_path_summary,
                    "targetPathSummary": item.target_path_summary,
                    "notes": item.notes,
                }
                for item in aggregate.file_transfer_records
            ],
        }
    )
    return payload


def _encode_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
