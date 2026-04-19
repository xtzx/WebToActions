from pydantic import Field

from app.core.domain_model import DomainModel


class ParameterSuggestion(DomainModel):
    name: str = Field(min_length=1)
    source: str = Field(min_length=1)
    example_value: str | None = None
    reason: str | None = None


class ActionFragmentSuggestion(DomainModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    stage_id: str = Field(min_length=1)
    request_ids: list[str] = Field(default_factory=list)
    notes: str | None = None
