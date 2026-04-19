from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.evidence.domain import FileTransferDirection, FileTransferRecord


@dataclass
class _TransferDraft:
    id: str
    direction: FileTransferDirection
    file_name: str
    occurred_at: datetime
    related_request_id: str | None


class FileTransferCollector:
    def __init__(self, *, recording_id: str) -> None:
        self._recording_id = recording_id
        self._transfers: list[_TransferDraft] = []

    def on_upload(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None:
        self._transfers.append(
            _TransferDraft(
                id=transfer_id,
                direction=FileTransferDirection.UPLOAD,
                file_name=file_name,
                occurred_at=datetime.now(UTC),
                related_request_id=related_request_id,
            )
        )

    def on_download(
        self,
        *,
        transfer_id: str,
        file_name: str,
        related_request_id: str | None,
    ) -> None:
        self._transfers.append(
            _TransferDraft(
                id=transfer_id,
                direction=FileTransferDirection.DOWNLOAD,
                file_name=file_name,
                occurred_at=datetime.now(UTC),
                related_request_id=related_request_id,
            )
        )

    def count(self) -> int:
        return len(self._transfers)

    def snapshot(self) -> tuple[FileTransferRecord, ...]:
        return tuple(
            FileTransferRecord(
                id=item.id,
                recording_id=self._recording_id,
                direction=item.direction,
                file_name=item.file_name,
                occurred_at=item.occurred_at,
                related_request_id=item.related_request_id,
            )
            for item in self._transfers
        )
