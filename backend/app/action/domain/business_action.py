from datetime import UTC, datetime

from typing import ClassVar
from typing import Self

from pydantic import Field, model_validator

from app.action.domain.action_kind import ActionKind
from app.action.domain.parameter_definition import ParameterDefinition
from app.core.domain_model import VersionedArtifactModel


class BusinessAction(VersionedArtifactModel):
    version_binding_fields: ClassVar[tuple[str, ...]] = ("source_action_macro_id",)
    version_timestamp_fields: ClassVar[tuple[str, ...]] = ("created_at",)

    name: str = Field(min_length=1)
    source_action_macro_id: str = Field(min_length=1)
    source_action_macro_version: int = Field(ge=1)
    business_steps: list[str] = Field(default_factory=list)
    parameter_definitions: list[ParameterDefinition] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_parameter_definitions(self) -> Self:
        for parameter_definition in self.parameter_definitions:
            if parameter_definition.action_id != self.id:
                raise ValueError(
                    "parameter_definitions action_id must match the business action id.",
                )

            if parameter_definition.owner_kind != ActionKind.BUSINESS_ACTION:
                raise ValueError(
                    "parameter_definitions owner_kind must be business_action for a business action.",
                )

        return self
