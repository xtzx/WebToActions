from enum import StrEnum
from typing import Any

from pydantic import Field

from app.action.domain.action_kind import ActionKind
from app.core.domain_model import DomainModel


class ParameterKind(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    URL = "url"
    FILE_PATH = "file_path"
    JSON = "json"


class ParameterDefinition(DomainModel):
    id: str = Field(min_length=1)
    action_id: str = Field(min_length=1)
    owner_kind: ActionKind
    name: str = Field(min_length=1)
    parameter_kind: ParameterKind
    required: bool = False
    default_value: Any | None = None
    injection_target: str = Field(min_length=1)
    description: str | None = None
