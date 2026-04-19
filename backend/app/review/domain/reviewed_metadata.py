from datetime import UTC, datetime
from typing import ClassVar

from pydantic import Field

from app.core.domain_model import VersionedArtifactModel


class ReviewedMetadata(VersionedArtifactModel):
    version_binding_fields: ClassVar[tuple[str, ...]] = (
        "recording_id",
        "source_draft_id",
    )
    version_timestamp_fields: ClassVar[tuple[str, ...]] = ("reviewed_at",)

    recording_id: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    source_draft_id: str = Field(min_length=1)
    source_draft_version: int = Field(ge=1)
    key_request_ids: list[str] = Field(default_factory=list)
    noise_request_ids: list[str] = Field(default_factory=list)
    field_descriptions: dict[str, str] = Field(default_factory=dict)
    parameter_source_map: dict[str, str] = Field(default_factory=dict)
    action_stage_ids: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
