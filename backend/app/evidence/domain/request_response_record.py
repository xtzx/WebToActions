from datetime import datetime

from pydantic import Field, model_validator
from typing import Self

from app.core.domain_model import DomainModel


class HttpHeader(DomainModel):
    name: str = Field(min_length=1)
    value: str


class RequestResponseRecord(DomainModel):
    id: str = Field(min_length=1)
    recording_id: str = Field(min_length=1)
    request_method: str = Field(min_length=1)
    request_url: str = Field(min_length=1)
    requested_at: datetime
    request_headers: list[HttpHeader] = Field(default_factory=list)
    request_body_blob_key: str | None = None
    response_status: int | None = None
    response_headers: list[HttpHeader] = Field(default_factory=list)
    response_body_blob_key: str | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    page_stage_id: str | None = None
    failure_reason: str | None = None

    @model_validator(mode="after")
    def validate_timing(self) -> Self:
        if self.finished_at is not None and self.finished_at < self.requested_at:
            raise ValueError("finished_at cannot be earlier than requested_at.")

        return self
