from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.action.domain import ActionMacro
from app.execution.api.serialization import serialize_execution_run

router = APIRouter(prefix="/actions", tags=["actions"])


class CreateActionMacroRequest(BaseModel):
    recording_id: str = Field(alias="recordingId", min_length=1)
    name: str | None = None
    description: str | None = None

    model_config = {"populate_by_name": True}


class StartExecutionRequest(BaseModel):
    browser_session_id: str = Field(alias="browserSessionId", min_length=1)
    parameters: dict[str, object] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


@router.get("")
def list_actions(request: Request) -> dict[str, list[dict[str, object]]]:
    orchestrator = request.app.state.action_orchestrator
    actions = orchestrator.list_actions()
    return {"items": [_serialize_action_summary(item) for item in actions]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_action_macro(
    payload: CreateActionMacroRequest,
    request: Request,
) -> dict[str, object]:
    orchestrator = request.app.state.action_orchestrator
    try:
        action = orchestrator.create_action_macro(
            recording_id=payload.recording_id,
            name=payload.name,
            description=payload.description,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _serialize_action_detail(action)


@router.get("/{action_id}")
def get_action_detail(action_id: str, request: Request) -> dict[str, object]:
    orchestrator = request.app.state.action_orchestrator
    action = orchestrator.get_action(action_id)
    if action is None:
        raise HTTPException(status_code=404, detail=f"Action macro {action_id} not found.")
    return _serialize_action_detail(action)


@router.post("/{action_id}/executions", status_code=status.HTTP_201_CREATED)
def start_execution(
    action_id: str,
    payload: StartExecutionRequest,
    request: Request,
) -> dict[str, object]:
    execution_service = request.app.state.execution_service
    try:
        run = execution_service.start_execution(
            action_id=action_id,
            browser_session_id=payload.browser_session_id,
            parameters=payload.parameters,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_execution_run(run)


def _serialize_action_summary(item: ActionMacro) -> dict[str, object]:
    return {
        "id": item.id,
        "version": item.version,
        "previousVersion": item.previous_version,
        "recordingId": item.recording_id,
        "name": item.name,
        "description": item.description,
        "stepCount": len(item.steps),
        "parameterCount": len(item.parameter_definitions),
        "createdAt": item.created_at.isoformat(),
    }


def _serialize_action_detail(item: ActionMacro) -> dict[str, object]:
    summary = _serialize_action_summary(item)
    summary.update(
        {
            "sourceReviewedMetadataId": item.source_reviewed_metadata_id,
            "sourceReviewedMetadataVersion": item.source_reviewed_metadata_version,
            "steps": [
                {
                    "id": step.id,
                    "stepKind": step.step_kind,
                    "title": step.title,
                    "requestId": step.request_id,
                    "requestMethod": step.request_method,
                    "requestUrl": step.request_url,
                    "pageStageId": step.page_stage_id,
                    "navigateUrl": step.navigate_url,
                }
                for step in item.steps
            ],
            "requiredPageStageIds": list(item.required_page_stage_ids),
            "parameterDefinitions": [
                {
                    "id": definition.id,
                    "actionId": definition.action_id,
                    "ownerKind": definition.owner_kind.value,
                    "name": definition.name,
                    "parameterKind": definition.parameter_kind.value,
                    "required": definition.required,
                    "defaultValue": definition.default_value,
                    "injectionTarget": definition.injection_target,
                    "description": definition.description,
                }
                for definition in item.parameter_definitions
            ],
            "sessionRequirements": list(item.session_requirements),
        }
    )
    return summary
