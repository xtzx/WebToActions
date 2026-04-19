from datetime import datetime

from pydantic import Field

from app.core.domain_model import DomainModel


class SessionStateSnapshot(DomainModel):
    id: str = Field(min_length=1)
    recording_id: str = Field(min_length=1)
    browser_session_id: str = Field(min_length=1)
    captured_at: datetime
    page_stage_id: str | None = None
    request_id: str | None = None
    cookie_summary: dict[str, str] = Field(default_factory=dict)
    storage_summary: dict[str, dict[str, str]] = Field(default_factory=dict)
