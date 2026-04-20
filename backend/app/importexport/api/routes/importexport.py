from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.importexport.service.import_service import ImportConflictError

router = APIRouter(prefix="/importexport", tags=["importexport"])


@router.get("/recordings/{recording_id}/bundle")
def export_recording_bundle(recording_id: str, request: Request) -> FileResponse:
    service = request.app.state.importexport_export_service
    try:
        result = service.export_recording_bundle(recording_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return FileResponse(
        result.archive_path,
        media_type="application/zip",
        filename=result.download_name,
    )


@router.post("/recordings/import", status_code=status.HTTP_201_CREATED)
async def import_recording_bundle(
    request: Request,
    file: UploadFile = File(...),
) -> dict[str, object]:
    service = request.app.state.importexport_import_service
    try:
        result = service.import_recording_bundle(await file.read())
    except ImportConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "recordingId": result.recording_id,
        "actionIds": result.action_ids,
        "executionIds": result.execution_ids,
        "warnings": result.warnings,
    }
