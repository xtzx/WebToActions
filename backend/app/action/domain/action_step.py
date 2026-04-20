from pydantic import Field

from app.core.domain_model import DomainModel


class ActionStep(DomainModel):
    id: str = Field(min_length=1)
    step_kind: str = Field(default="request_replay", min_length=1)
    title: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    request_method: str = Field(min_length=1)
    request_url: str = Field(min_length=1)
    page_stage_id: str | None = None
    navigate_url: str | None = None
