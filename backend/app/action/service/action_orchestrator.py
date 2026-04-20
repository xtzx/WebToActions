from __future__ import annotations

import json
from urllib.parse import urlparse

from app.action.domain import ActionKind, ActionMacro, ActionStep, ParameterDefinition, ParameterKind
from app.action.repository import ActionMacroRepository
from app.recording.domain.recording import RecordingStatus
from app.recording.repository import RecordingAggregate, RecordingRepository
from app.review.domain.metadata_draft import MetadataDraft
from app.review.domain.reviewed_metadata import ReviewedMetadata


class ActionOrchestrator:
    def __init__(
        self,
        *,
        recording_repository: RecordingRepository,
        action_repository: ActionMacroRepository,
    ) -> None:
        self._recording_repository = recording_repository
        self._action_repository = action_repository

    def list_actions(self) -> tuple[ActionMacro, ...]:
        return self._action_repository.list()

    def get_action(self, action_id: str, version: int | None = None) -> ActionMacro | None:
        return self._action_repository.get(action_id, version)

    def create_action_macro(
        self,
        *,
        recording_id: str,
        name: str | None = None,
        description: str | None = None,
    ) -> ActionMacro:
        aggregate = self._recording_repository.get(recording_id)
        if aggregate is None:
            raise KeyError(f"Recording {recording_id} not found.")

        reviewed = self._latest_reviewed_metadata(aggregate)
        if reviewed is None:
            raise ValueError("Latest reviewed metadata is required before generating an action macro.")

        action_id = aggregate.recording.generated_action_macro_id or f"macro-{recording_id}"
        existing = self._action_repository.get(action_id)
        next_version = 1 if existing is None else existing.version + 1
        parameter_definitions = self._build_parameter_definitions(
            action_id=action_id,
            version=next_version,
            reviewed=reviewed,
            aggregate=aggregate,
        )
        steps = self._build_steps(reviewed=reviewed, aggregate=aggregate)
        session_requirements = self._session_requirements(aggregate)

        if existing is None:
            action = ActionMacro(
                id=action_id,
                version=1,
                previous_version=None,
                recording_id=recording_id,
                name=name or f"{aggregate.recording.name} 执行宏",
                source_reviewed_metadata_id=reviewed.id,
                source_reviewed_metadata_version=reviewed.version,
                description=description or "基于已审核录制自动生成的请求回放宏。",
                steps=steps,
                required_page_stage_ids=list(reviewed.action_stage_ids),
                parameter_definitions=parameter_definitions,
                session_requirements=session_requirements,
            )
        else:
            action = existing.next_version(
                name=name or existing.name,
                source_reviewed_metadata_id=reviewed.id,
                source_reviewed_metadata_version=reviewed.version,
                description=description or existing.description or "基于已审核录制自动生成的请求回放宏。",
                steps=steps,
                required_page_stage_ids=list(reviewed.action_stage_ids),
                parameter_definitions=parameter_definitions,
                session_requirements=session_requirements,
            )

        self._action_repository.save(action)
        self._persist_recording_generation(aggregate=aggregate, action=action)
        return action

    def _latest_reviewed_metadata(
        self,
        aggregate: RecordingAggregate,
    ) -> ReviewedMetadata | None:
        if not aggregate.reviewed_metadata:
            return None
        return aggregate.reviewed_metadata[-1]

    def _build_steps(
        self,
        *,
        reviewed: ReviewedMetadata,
        aggregate: RecordingAggregate,
    ) -> list[ActionStep]:
        request_by_id = {item.id: item for item in aggregate.request_response_records}
        page_stage_by_id = {item.id: item for item in aggregate.page_stages}
        request_order = {item.id: index for index, item in enumerate(aggregate.request_response_records)}
        ordered_request_ids = sorted(
            reviewed.key_request_ids,
            key=lambda item: request_order.get(item, 10_000),
        )

        steps: list[ActionStep] = []
        for index, request_id in enumerate(ordered_request_ids, start=1):
            request = request_by_id.get(request_id)
            if request is None:
                raise ValueError(f"Reviewed request {request_id} does not exist in recording evidence.")
            stage = (
                page_stage_by_id.get(request.page_stage_id)
                if request.page_stage_id is not None
                else None
            )
            steps.append(
                ActionStep(
                    id=f"step-{index}",
                    title=f"{request.request_method} {request.request_url}",
                    request_id=request.id,
                    request_method=request.request_method,
                    request_url=request.request_url,
                    page_stage_id=request.page_stage_id,
                    navigate_url=stage.url if stage is not None else None,
                )
            )
        return steps

    def _build_parameter_definitions(
        self,
        *,
        action_id: str,
        version: int,
        reviewed: ReviewedMetadata,
        aggregate: RecordingAggregate,
    ) -> list[ParameterDefinition]:
        draft = self._source_draft(reviewed=reviewed, aggregate=aggregate)
        suggestion_by_name = {
            item.name: item
            for item in draft.parameter_suggestions
        } if draft is not None else {}

        definitions: list[ParameterDefinition] = []
        for index, (name, injection_target) in enumerate(reviewed.parameter_source_map.items(), start=1):
            suggestion = suggestion_by_name.get(name)
            example_value = suggestion.example_value if suggestion is not None else None
            definitions.append(
                ParameterDefinition(
                    id=f"{action_id}-v{version}-param-{index}",
                    action_id=action_id,
                    owner_kind=ActionKind.ACTION_MACRO,
                    name=name,
                    parameter_kind=_infer_parameter_kind(example_value),
                    required=True,
                    default_value=None,
                    injection_target=injection_target,
                    description=reviewed.field_descriptions.get(name),
                )
            )
        return definitions

    def _source_draft(
        self,
        *,
        reviewed: ReviewedMetadata,
        aggregate: RecordingAggregate,
    ) -> MetadataDraft | None:
        for item in aggregate.metadata_drafts:
            if (
                item.id == reviewed.source_draft_id
                and item.version == reviewed.source_draft_version
            ):
                return item
        return None

    def _session_requirements(self, aggregate: RecordingAggregate) -> list[str]:
        if aggregate.browser_session is not None and aggregate.browser_session.login_site_summaries:
            return list(aggregate.browser_session.login_site_summaries)
        netloc = urlparse(aggregate.recording.start_url).netloc
        return [netloc] if netloc else []

    def _persist_recording_generation(
        self,
        *,
        aggregate: RecordingAggregate,
        action: ActionMacro,
    ) -> None:
        recording = aggregate.recording
        if recording.status == RecordingStatus.PENDING_REVIEW:
            updated_recording = recording.mark_macro_generated(action_macro_id=action.id)
        elif recording.status == RecordingStatus.MACRO_GENERATED:
            updated_recording = recording.validated_copy(
                generated_action_macro_id=action.id,
            )
        else:
            raise ValueError("Action macros can only be generated after review has completed.")

        self._recording_repository.save_recording(updated_recording)


def _infer_parameter_kind(example_value: str | None) -> ParameterKind:
    if example_value is None:
        return ParameterKind.STRING

    stripped = example_value.strip()
    if not stripped:
        return ParameterKind.STRING
    if stripped.isdigit():
        return ParameterKind.INTEGER
    if stripped.lower() in {"true", "false"}:
        return ParameterKind.BOOLEAN
    if stripped.startswith("http://") or stripped.startswith("https://"):
        return ParameterKind.URL
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            json.loads(stripped)
        except json.JSONDecodeError:
            return ParameterKind.STRING
        return ParameterKind.JSON
    return ParameterKind.STRING
