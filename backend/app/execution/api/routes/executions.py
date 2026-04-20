from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.execution.api.serialization import encode_sse, serialize_execution_run
from app.execution.service.execution_service import serialize_execution_snapshot

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("")
def list_executions(request: Request) -> dict[str, list[dict[str, object]]]:
    execution_service = request.app.state.execution_service
    runs = execution_service.list_runs()
    return {"items": [serialize_execution_run(item) for item in runs]}


@router.get("/{execution_id}")
def get_execution_detail(execution_id: str, request: Request) -> dict[str, object]:
    execution_service = request.app.state.execution_service
    run = execution_service.get_run(execution_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Execution run {execution_id} not found.")
    return serialize_execution_run(run)


@router.get("/{execution_id}/events")
def stream_execution_events(
    execution_id: str,
    request: Request,
    once: bool = False,
) -> StreamingResponse:
    execution_service = request.app.state.execution_service
    latest, queue = execution_service.subscribe(execution_id)
    if latest is None and execution_service.get_run(execution_id) is None:
        execution_service.unsubscribe(execution_id, queue)
        raise HTTPException(status_code=404, detail=f"Execution run {execution_id} not found.")

    async def event_stream():
        try:
            if latest is not None:
                yield encode_sse(serialize_execution_snapshot(latest))
            if once:
                return
            while not await request.is_disconnected():
                snapshot = await asyncio.to_thread(
                    execution_service.wait_for_event,
                    queue,
                    timeout_seconds=1.0,
                )
                if snapshot is None:
                    yield ": keep-alive\n\n"
                    continue
                yield encode_sse(serialize_execution_snapshot(snapshot))
        finally:
            execution_service.unsubscribe(execution_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
