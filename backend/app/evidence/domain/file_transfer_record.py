from datetime import datetime
from enum import StrEnum

from pydantic import Field

from app.core.domain_model import DomainModel


class FileTransferDirection(StrEnum):
    UPLOAD = "upload"
    DOWNLOAD = "download"


class FileTransferRecord(DomainModel):
    id: str = Field(min_length=1)
    recording_id: str = Field(min_length=1)
    direction: FileTransferDirection
    file_name: str = Field(min_length=1)
    occurred_at: datetime
    related_request_id: str | None = None
    source_path_summary: str | None = None
    target_path_summary: str | None = None
    notes: str | None = None
