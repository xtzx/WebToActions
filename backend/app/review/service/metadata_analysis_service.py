from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

from app.recording.repository import RecordingAggregate, RecordingRepository
from app.review.domain import (
    ActionFragmentSuggestion,
    MetadataDraft,
    ParameterSuggestion,
)


class MetadataAnalysisService:
    def __init__(
        self,
        *,
        recording_repository: RecordingRepository,
        storage_root: Path,
    ) -> None:
        self._recording_repository = recording_repository
        self._storage_root = storage_root

    def analyze_recording(self, recording_id: str) -> MetadataDraft:
        aggregate = self._recording_repository.get(recording_id)
        if aggregate is None:
            raise KeyError(f"Recording {recording_id} does not exist.")

        candidate_request_ids = self._candidate_request_ids(aggregate)
        parameter_suggestions = self._parameter_suggestions(aggregate)
        action_fragment_suggestions = self._action_fragments(aggregate)
        analysis_notes = (
            "阶段 4 MVP 使用确定性规则生成 metadata draft，"
            f"候选请求 {len(candidate_request_ids)} 个，"
            f"参数建议 {len(parameter_suggestions)} 个，"
            f"动作片段 {len(action_fragment_suggestions)} 个。"
        )

        latest_draft = aggregate.metadata_drafts[-1] if aggregate.metadata_drafts else None
        if latest_draft is None:
            draft = MetadataDraft(
                id=f"draft-{recording_id}",
                recording_id=recording_id,
                version=1,
                candidate_request_ids=candidate_request_ids,
                parameter_suggestions=parameter_suggestions,
                action_fragment_suggestions=action_fragment_suggestions,
                analysis_notes=analysis_notes,
            )
        else:
            draft = latest_draft.next_version(
                candidate_request_ids=candidate_request_ids,
                parameter_suggestions=parameter_suggestions,
                action_fragment_suggestions=action_fragment_suggestions,
                analysis_notes=analysis_notes,
            )

        updated_aggregate = replace(
            aggregate,
            metadata_drafts=(*aggregate.metadata_drafts, draft),
        )
        self._recording_repository.save(updated_aggregate)
        return draft

    def _candidate_request_ids(self, aggregate: RecordingAggregate) -> list[str]:
        request_ids: list[str] = []
        for item in aggregate.request_response_records:
            if item.request_method.upper() in {"POST", "PUT", "PATCH", "DELETE"}:
                request_ids.append(item.id)
                continue
            if item.request_body_blob_key is not None:
                request_ids.append(item.id)
        return request_ids or [item.id for item in aggregate.request_response_records]

    def _parameter_suggestions(
        self,
        aggregate: RecordingAggregate,
    ) -> list[ParameterSuggestion]:
        suggestions: list[ParameterSuggestion] = []
        seen_names: set[str] = set()

        for item in aggregate.request_response_records:
            if item.request_body_blob_key is None:
                continue
            payload = self._load_json_blob(item.request_body_blob_key)
            if not isinstance(payload, dict):
                continue

            for key, value in payload.items():
                if key in seen_names:
                    continue
                seen_names.add(key)
                suggestions.append(
                    ParameterSuggestion(
                        name=str(key),
                        source=f"request.body.{key}",
                        example_value=None if value is None else str(value),
                        reason="检测到请求体中的候选参数字段。",
                    )
                )

        return suggestions

    def _action_fragments(
        self,
        aggregate: RecordingAggregate,
    ) -> list[ActionFragmentSuggestion]:
        suggestions: list[ActionFragmentSuggestion] = []
        for index, stage in enumerate(aggregate.page_stages, start=1):
            if not stage.related_request_ids:
                continue
            suggestions.append(
                ActionFragmentSuggestion(
                    id=f"fragment-{index}",
                    title=stage.name,
                    stage_id=stage.id,
                    request_ids=list(stage.related_request_ids),
                    notes=f"页面阶段 {stage.name} 覆盖 {len(stage.related_request_ids)} 个候选请求。",
                )
            )

        if suggestions:
            return suggestions

        return [
            ActionFragmentSuggestion(
                id="fragment-1",
                title="默认动作片段",
                stage_id=aggregate.page_stages[0].id if aggregate.page_stages else "stage-unknown",
                request_ids=[item.id for item in aggregate.request_response_records],
                notes="未识别到明确的页面阶段归并，使用默认片段。",
            )
        ]

    def _load_json_blob(self, blob_key: str) -> Any:
        path = self._storage_root / blob_key
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
