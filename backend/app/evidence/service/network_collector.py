from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.evidence.domain import HttpHeader, RequestResponseRecord
from app.evidence.service.evidence_writer import EvidenceWriter
from app.evidence.service.page_stage_tracker import PageStageTracker


@dataclass
class _ObservedRequest:
    id: str
    method: str
    url: str
    requested_at: datetime
    request_headers: list[tuple[str, str]]
    request_body: bytes | None
    page_stage_id: str | None
    resource_type: str
    is_navigation_request: bool
    response_status: int | None = None
    response_headers: list[tuple[str, str]] = field(default_factory=list)
    response_body: bytes | None = None
    finished_at: datetime | None = None
    failure_reason: str | None = None


class NetworkCollector:
    def __init__(
        self,
        *,
        recording_id: str,
        page_stage_tracker: PageStageTracker,
    ) -> None:
        self._recording_id = recording_id
        self._page_stage_tracker = page_stage_tracker
        self._requests: list[_ObservedRequest] = []
        self._request_index: dict[str, _ObservedRequest] = {}

    def on_request(
        self,
        *,
        request_id: str,
        method: str,
        url: str,
        headers: list[tuple[str, str]],
        body: bytes | None,
        resource_type: str,
        is_navigation_request: bool,
    ) -> None:
        page_stage_id = self._page_stage_tracker.link_request(request_id)
        observed = _ObservedRequest(
            id=request_id,
            method=method,
            url=url,
            requested_at=datetime.now(UTC),
            request_headers=headers,
            request_body=body,
            page_stage_id=page_stage_id,
            resource_type=resource_type,
            is_navigation_request=is_navigation_request,
        )
        self._requests.append(observed)
        self._request_index[request_id] = observed

    def on_response(
        self,
        *,
        request_id: str,
        status: int,
        status_text: str,
        headers: list[tuple[str, str]],
        body: bytes | None,
    ) -> None:
        request = self._request_index.get(request_id)
        if request is None:
            return

        request.response_status = status
        request.response_headers = headers + [("x-status-text", status_text)]
        request.response_body = body
        request.finished_at = datetime.now(UTC)

    def on_request_failed(self, *, request_id: str, reason: str) -> None:
        request = self._request_index.get(request_id)
        if request is None:
            return

        request.failure_reason = reason
        request.finished_at = datetime.now(UTC)

    def count(self) -> int:
        return len(self._requests)

    def failed_count(self) -> int:
        return sum(1 for request in self._requests if request.failure_reason is not None)

    def snapshot(self) -> tuple[RequestResponseRecord, ...]:
        return tuple(self._build_record(request, evidence_writer=None) for request in self._requests)

    def export(self, *, evidence_writer: EvidenceWriter) -> tuple[RequestResponseRecord, ...]:
        return tuple(
            self._build_record(request, evidence_writer=evidence_writer)
            for request in self._requests
        )

    def _build_record(
        self,
        request: _ObservedRequest,
        *,
        evidence_writer: EvidenceWriter | None,
    ) -> RequestResponseRecord:
        request_body_blob_key = None
        response_body_blob_key = None
        if evidence_writer is not None:
            request_body_blob_key = evidence_writer.write_request_body(
                recording_id=self._recording_id,
                request_id=request.id,
                payload=request.request_body,
            )
            response_body_blob_key = evidence_writer.write_response_body(
                recording_id=self._recording_id,
                request_id=request.id,
                payload=request.response_body,
            )

        duration_ms = None
        if request.finished_at is not None:
            duration_ms = max(
                0,
                int((request.finished_at - request.requested_at).total_seconds() * 1000),
            )

        return RequestResponseRecord(
            id=request.id,
            recording_id=self._recording_id,
            request_method=request.method,
            request_url=request.url,
            requested_at=request.requested_at,
            request_headers=_headers(request.request_headers),
            request_body_blob_key=request_body_blob_key,
            response_status=request.response_status,
            response_headers=_headers(request.response_headers),
            response_body_blob_key=response_body_blob_key,
            finished_at=request.finished_at,
            duration_ms=duration_ms,
            page_stage_id=request.page_stage_id,
            failure_reason=request.failure_reason,
        )


def _headers(items: list[tuple[str, str]]) -> list[HttpHeader]:
    return [HttpHeader(name=name, value=value) for name, value in items]
