from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.recording.repository import RecordingAggregate
from app.review.domain import MetadataDraft, ReviewedMetadata
from app.review.service.review_job_runner import (
    ReviewAnalysisUnavailableError,
    serialize_review_snapshot,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])


class SaveReviewedMetadataRequest(BaseModel):
    reviewer: str = Field(min_length=1)
    source_draft_id: str = Field(alias="sourceDraftId", min_length=1)
    source_draft_version: int = Field(alias="sourceDraftVersion", ge=1)
    key_request_ids: list[str] = Field(alias="keyRequestIds", default_factory=list)
    noise_request_ids: list[str] = Field(
        alias="noiseRequestIds",
        default_factory=list,
    )
    field_descriptions: dict[str, str] = Field(
        alias="fieldDescriptions",
        default_factory=dict,
    )
    parameter_source_map: dict[str, str] = Field(
        alias="parameterSourceMap",
        default_factory=dict,
    )
    action_stage_ids: list[str] = Field(alias="actionStageIds", default_factory=list)
    risk_flags: list[str] = Field(alias="riskFlags", default_factory=list)

    model_config = {"populate_by_name": True}


@router.get("/{recording_id}")
def get_review_context(recording_id: str, request: Request) -> dict[str, object]:
    review_service = request.app.state.review_service
    review_job_runner = request.app.state.review_job_runner

    aggregate = review_service.get_review_aggregate(recording_id)
    if aggregate is None:
        raise HTTPException(status_code=404, detail="Recording not found.")

    if not aggregate.metadata_drafts:
        try:
            review_job_runner.ensure_started(recording_id)
        except ReviewAnalysisUnavailableError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        aggregate = review_service.get_review_aggregate(recording_id)
        if aggregate is None:
            raise HTTPException(status_code=404, detail="Recording not found.")

    snapshot = review_job_runner.get_snapshot(recording_id)
    latest_draft = review_service.latest_draft(aggregate)
    latest_reviewed_metadata = review_service.latest_reviewed_metadata(aggregate)
    return {
        "recordingId": recording_id,
        "analysisStatus": snapshot.status if snapshot is not None else "completed",
        "latestDraft": _serialize_metadata_draft(latest_draft),
        "latestReviewedMetadata": _serialize_reviewed_metadata(latest_reviewed_metadata),
        "reviewHistory": [
            _serialize_reviewed_metadata(item)
            for item in review_service.review_history(aggregate)
        ],
        "requests": [
            {
                "id": item.id,
                "requestMethod": item.request_method,
                "requestUrl": item.request_url,
                "responseStatus": item.response_status,
                "pageStageId": item.page_stage_id,
            }
            for item in aggregate.request_response_records
        ],
        "pageStages": [
            {
                "id": item.id,
                "name": item.name,
                "url": item.url,
                "relatedRequestIds": list(item.related_request_ids),
            }
            for item in aggregate.page_stages
        ],
    }


@router.post("/{recording_id}/analysis")
def enqueue_review_analysis(recording_id: str, request: Request) -> dict[str, object]:
    review_job_runner = request.app.state.review_job_runner
    try:
        snapshot = review_job_runner.ensure_started(recording_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewAnalysisUnavailableError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return serialize_review_snapshot(snapshot)


@router.get("/{recording_id}/events")
def stream_review_events(
    recording_id: str,
    request: Request,
    once: bool = False,
) -> StreamingResponse:
    review_job_runner = request.app.state.review_job_runner
    try:
        latest, queue = review_job_runner.subscribe(recording_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if latest is None:
        try:
            review_job_runner.ensure_started(recording_id)
        except KeyError as exc:
            review_job_runner.unsubscribe(recording_id, queue)
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ReviewAnalysisUnavailableError as exc:
            review_job_runner.unsubscribe(recording_id, queue)
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        latest = review_job_runner.get_snapshot(recording_id)

    async def event_stream():
        try:
            if latest is not None:
                yield _encode_sse(serialize_review_snapshot(latest))
            if once:
                return
            while not await request.is_disconnected():
                snapshot = await asyncio.to_thread(
                    review_job_runner.wait_for_event,
                    queue,
                    timeout_seconds=1.0,
                )
                if snapshot is None:
                    yield ": keep-alive\n\n"
                    continue
                yield _encode_sse(serialize_review_snapshot(snapshot))
        finally:
            review_job_runner.unsubscribe(recording_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.post(
    "/{recording_id}/reviewed-metadata",
    status_code=status.HTTP_201_CREATED,
)
def save_reviewed_metadata(
    recording_id: str,
    payload: SaveReviewedMetadataRequest,
    request: Request,
) -> dict[str, object]:
    review_service = request.app.state.review_service
    try:
        reviewed = review_service.save_reviewed_metadata(
            recording_id=recording_id,
            reviewer=payload.reviewer,
            source_draft_id=payload.source_draft_id,
            source_draft_version=payload.source_draft_version,
            key_request_ids=payload.key_request_ids,
            noise_request_ids=payload.noise_request_ids,
            field_descriptions=payload.field_descriptions,
            parameter_source_map=payload.parameter_source_map,
            action_stage_ids=payload.action_stage_ids,
            risk_flags=payload.risk_flags,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_reviewed_metadata(reviewed)


def _serialize_metadata_draft(draft: MetadataDraft | None) -> dict[str, object] | None:
    if draft is None:
        return None
    return {
        "id": draft.id,
        "version": draft.version,
        "previousVersion": draft.previous_version,
        "recordingId": draft.recording_id,
        "candidateRequestIds": list(draft.candidate_request_ids),
        "parameterSuggestions": [
            {
                "name": item.name,
                "source": item.source,
                "exampleValue": item.example_value,
                "reason": item.reason,
            }
            for item in draft.parameter_suggestions
        ],
        "actionFragmentSuggestions": [
            {
                "id": item.id,
                "title": item.title,
                "stageId": item.stage_id,
                "requestIds": list(item.request_ids),
                "notes": item.notes,
            }
            for item in draft.action_fragment_suggestions
        ],
        "analysisNotes": draft.analysis_notes,
        "generatedAt": draft.generated_at.isoformat(),
    }


def _serialize_reviewed_metadata(
    reviewed: ReviewedMetadata | None,
) -> dict[str, object] | None:
    if reviewed is None:
        return None
    return {
        "id": reviewed.id,
        "version": reviewed.version,
        "previousVersion": reviewed.previous_version,
        "recordingId": reviewed.recording_id,
        "reviewer": reviewed.reviewer,
        "sourceDraftId": reviewed.source_draft_id,
        "sourceDraftVersion": reviewed.source_draft_version,
        "keyRequestIds": list(reviewed.key_request_ids),
        "noiseRequestIds": list(reviewed.noise_request_ids),
        "fieldDescriptions": dict(reviewed.field_descriptions),
        "parameterSourceMap": dict(reviewed.parameter_source_map),
        "actionStageIds": list(reviewed.action_stage_ids),
        "riskFlags": list(reviewed.risk_flags),
        "reviewedAt": reviewed.reviewed_at.isoformat(),
    }


def _encode_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
