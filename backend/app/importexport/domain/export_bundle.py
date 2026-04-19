from datetime import UTC, datetime
from enum import StrEnum
from typing import ClassVar

from pydantic import Field

from app.core.domain_model import DomainModel, VersionedArtifactModel


class ExportScope(StrEnum):
    RECORDING = "recording"
    ACTION_LIBRARY = "action_library"
    FULL = "full"


class VersionedArtifactReference(DomainModel):
    artifact_id: str = Field(min_length=1)
    version: int = Field(ge=1)


class ExportBundle(VersionedArtifactModel):
    version_binding_fields: ClassVar[tuple[str, ...]] = ("export_scope",)
    version_timestamp_fields: ClassVar[tuple[str, ...]] = ("exported_at",)

    export_scope: ExportScope
    package_format_version: str = Field(min_length=1)
    recording_ids: list[str] = Field(default_factory=list)
    reviewed_metadata_refs: list[VersionedArtifactReference] = Field(
        default_factory=list,
    )
    action_macro_refs: list[VersionedArtifactReference] = Field(default_factory=list)
    business_action_refs: list[VersionedArtifactReference] = Field(default_factory=list)
    file_manifest: list[str] = Field(default_factory=list)
    exported_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
