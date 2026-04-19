from datetime import datetime
from typing import Self

from pydantic import Field, model_validator

from app.core.domain_model import DomainModel


class PageStage(DomainModel):
    id: str = Field(min_length=1)
    recording_id: str = Field(min_length=1)
    url: str = Field(min_length=1)
    name: str = Field(min_length=1)
    started_at: datetime
    ended_at: datetime | None = None
    related_request_ids: list[str] = Field(default_factory=list)
    wait_points: list[str] = Field(default_factory=list)
    observable_state: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timing(self) -> Self:
        if self.ended_at is not None and self.ended_at < self.started_at:
            raise ValueError("ended_at cannot be earlier than started_at.")

        return self
