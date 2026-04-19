from datetime import UTC, datetime
from typing import ClassVar

from pydantic import Field

from app.core.domain_model import VersionedArtifactModel
from app.review.domain.suggestions import ActionFragmentSuggestion, ParameterSuggestion


class MetadataDraft(VersionedArtifactModel):
    version_binding_fields: ClassVar[tuple[str, ...]] = ("recording_id",)
    version_timestamp_fields: ClassVar[tuple[str, ...]] = ("generated_at",)

    recording_id: str = Field(min_length=1)
    candidate_request_ids: list[str] = Field(default_factory=list)
    parameter_suggestions: list[ParameterSuggestion] = Field(default_factory=list)
    action_fragment_suggestions: list[ActionFragmentSuggestion] = Field(
        default_factory=list
    )
    analysis_notes: str | None = None
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
