from datetime import UTC, datetime

from typing import ClassVar
from typing import Self

from pydantic import Field, model_validator

from app.action.domain.action_step import ActionStep
from app.action.domain.action_kind import ActionKind
from app.action.domain.parameter_definition import ParameterDefinition
from app.core.domain_model import VersionedArtifactModel


class ActionMacro(VersionedArtifactModel):
    version_binding_fields: ClassVar[tuple[str, ...]] = (
        "recording_id",
        "source_reviewed_metadata_id",
    )
    version_timestamp_fields: ClassVar[tuple[str, ...]] = ("created_at",)

    recording_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    source_reviewed_metadata_id: str = Field(min_length=1)
    source_reviewed_metadata_version: int = Field(ge=1)
    description: str | None = None
    steps: list[ActionStep] = Field(default_factory=list)
    required_page_stage_ids: list[str] = Field(default_factory=list)
    parameter_definitions: list[ParameterDefinition] = Field(default_factory=list)
    session_requirements: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_parameter_definitions(self) -> Self:
        for parameter_definition in self.parameter_definitions:
            if parameter_definition.action_id != self.id:
                raise ValueError(
                    "parameter_definitions action_id must match the action macro id.",
                )

            if parameter_definition.owner_kind != ActionKind.ACTION_MACRO:
                raise ValueError(
                    "parameter_definitions owner_kind must be action_macro for an action macro.",
                )

        return self
