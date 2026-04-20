from datetime import UTC, datetime

from sqlalchemy import delete, insert, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.evidence.domain import (
    FileTransferRecord,
    HttpHeader,
    PageStage,
    RequestResponseRecord,
    SessionStateSnapshot,
)
from app.infrastructure.db.schema import (
    browser_session,
    file_transfer_record,
    metadata_draft,
    page_stage,
    recording,
    request_response_record,
    reviewed_metadata,
    session_state_snapshot,
)
from app.recording.domain.recording import Recording
from app.recording.repository import RecordingAggregate
from app.review.domain.metadata_draft import MetadataDraft
from app.review.domain.reviewed_metadata import ReviewedMetadata
from app.session.domain.browser_session import BrowserSession


class SqliteRecordingRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save_recording(self, item: Recording) -> None:
        with self._session_factory.begin() as session:
            existing = session.execute(
                select(recording.c.id).where(recording.c.id == item.id)
            ).first()
            row = self._recording_only_row(item)
            if existing is None:
                session.execute(insert(recording).values(row))
            else:
                session.execute(
                    update(recording)
                    .where(recording.c.id == item.id)
                    .values(row)
                )

    def save(
        self,
        aggregate: RecordingAggregate,
        *,
        session: Session | None = None,
    ) -> None:
        if session is None:
            with self._session_factory.begin() as managed_session:
                self._save_in_session(managed_session, aggregate)
            return

        self._save_in_session(session, aggregate)

    def _save_in_session(self, session: Session, aggregate: RecordingAggregate) -> None:
        if aggregate.browser_session is not None:
            browser_session_row = self._browser_session_row(aggregate.browser_session)
            existing_session = session.execute(
                select(browser_session.c.id).where(
                    browser_session.c.id == aggregate.browser_session.id
                )
            ).first()
            if existing_session is None:
                session.execute(insert(browser_session).values(browser_session_row))
            else:
                session.execute(
                    update(browser_session)
                    .where(browser_session.c.id == aggregate.browser_session.id)
                    .values(browser_session_row)
                )

        recording_id = aggregate.recording.id
        session.execute(
            delete(file_transfer_record).where(
                file_transfer_record.c.recording_id == recording_id
            )
        )
        session.execute(
            delete(session_state_snapshot).where(
                session_state_snapshot.c.recording_id == recording_id
            )
        )
        session.execute(
            delete(request_response_record).where(
                request_response_record.c.recording_id == recording_id
            )
        )
        session.execute(
            delete(page_stage).where(page_stage.c.recording_id == recording_id)
        )
        session.execute(
            delete(reviewed_metadata).where(
                reviewed_metadata.c.recording_id == recording_id
            )
        )
        session.execute(
            delete(metadata_draft).where(
                metadata_draft.c.recording_id == recording_id
            )
        )
        session.execute(delete(recording).where(recording.c.id == recording_id))
        session.execute(insert(recording).values(self._recording_row(aggregate)))

        if aggregate.page_stages:
            session.execute(
                insert(page_stage),
                [self._page_stage_row(item) for item in aggregate.page_stages],
            )

        if aggregate.request_response_records:
            session.execute(
                insert(request_response_record),
                [
                    self._request_response_row(item)
                    for item in aggregate.request_response_records
                ],
            )

        if aggregate.session_state_snapshots:
            session.execute(
                insert(session_state_snapshot),
                [
                    self._session_state_row(item)
                    for item in aggregate.session_state_snapshots
                ],
            )

        if aggregate.file_transfer_records:
            session.execute(
                insert(file_transfer_record),
                [self._file_transfer_row(item) for item in aggregate.file_transfer_records],
            )

        if aggregate.metadata_drafts:
            session.execute(
                insert(metadata_draft),
                [self._metadata_draft_row(item) for item in aggregate.metadata_drafts],
            )

        if aggregate.reviewed_metadata:
            session.execute(
                insert(reviewed_metadata),
                [self._reviewed_metadata_row(item) for item in aggregate.reviewed_metadata],
            )

    def get(self, recording_id: str) -> RecordingAggregate | None:
        with self._session_factory() as session:
            recording_row = session.execute(
                select(recording).where(recording.c.id == recording_id)
            ).mappings().first()
            if recording_row is None:
                return None
            return self._load_aggregate(session, recording_row)

    def list(self) -> tuple[RecordingAggregate, ...]:
        with self._session_factory() as session:
            rows = session.execute(
                select(recording).order_by(recording.c.created_at.desc())
            ).mappings()
            return tuple(self._load_aggregate(session, row) for row in rows)

    def _load_aggregate(self, session: Session, recording_row) -> RecordingAggregate:  # type: ignore[no-untyped-def]
        recording_id = recording_row["id"]
        browser_session_row = session.execute(
            select(browser_session).where(
                browser_session.c.id == recording_row["browser_session_id"]
            )
        ).mappings().first()
        page_stage_rows = session.execute(
            select(page_stage)
            .where(page_stage.c.recording_id == recording_id)
            .order_by(page_stage.c.started_at.asc())
        ).mappings()
        request_rows = session.execute(
            select(request_response_record)
            .where(request_response_record.c.recording_id == recording_id)
            .order_by(request_response_record.c.requested_at.asc())
        ).mappings()
        snapshot_rows = session.execute(
            select(session_state_snapshot)
            .where(session_state_snapshot.c.recording_id == recording_id)
            .order_by(session_state_snapshot.c.captured_at.asc())
        ).mappings()
        transfer_rows = session.execute(
            select(file_transfer_record)
            .where(file_transfer_record.c.recording_id == recording_id)
            .order_by(file_transfer_record.c.occurred_at.asc())
        ).mappings()
        draft_rows = session.execute(
            select(metadata_draft)
            .where(metadata_draft.c.recording_id == recording_id)
            .order_by(metadata_draft.c.version.asc())
        ).mappings()
        reviewed_rows = session.execute(
            select(reviewed_metadata)
            .where(reviewed_metadata.c.recording_id == recording_id)
            .order_by(reviewed_metadata.c.version.asc())
        ).mappings()

        return RecordingAggregate(
            recording=self._load_recording(recording_row),
            browser_session=(
                self._load_browser_session(browser_session_row)
                if browser_session_row is not None
                else None
            ),
            page_stages=tuple(self._load_page_stage(row) for row in page_stage_rows),
            request_response_records=tuple(
                self._load_request_response(row) for row in request_rows
            ),
            session_state_snapshots=tuple(
                self._load_session_state_snapshot(row) for row in snapshot_rows
            ),
            file_transfer_records=tuple(
                self._load_file_transfer(row) for row in transfer_rows
            ),
            metadata_drafts=tuple(self._load_metadata_draft(row) for row in draft_rows),
            reviewed_metadata=tuple(
                self._load_reviewed_metadata(row) for row in reviewed_rows
            ),
        )

    def _browser_session_row(self, item: BrowserSession) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "profile_id": payload["profile_id"],
            "status": payload["status"],
            "login_site_summaries_json": payload["login_site_summaries"],
            "created_at": item.created_at,
            "last_activity_at": item.last_activity_at,
        }

    def _recording_row(self, aggregate: RecordingAggregate) -> dict[str, object]:
        return self._recording_only_row(aggregate.recording)

    def _recording_only_row(self, item: Recording) -> dict[str, object]:
        return {
            "id": item.id,
            "name": item.name,
            "start_url": item.start_url,
            "browser_session_id": item.browser_session_id,
            "status": item.status.value,
            "created_at": item.created_at,
            "started_at": item.started_at,
            "ended_at": item.ended_at,
            "generated_action_macro_id": item.generated_action_macro_id,
        }

    def _page_stage_row(self, item: PageStage) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "recording_id": payload["recording_id"],
            "url": payload["url"],
            "name": payload["name"],
            "started_at": item.started_at,
            "ended_at": item.ended_at,
            "related_request_ids_json": payload["related_request_ids"],
            "wait_points_json": payload["wait_points"],
            "observable_state_json": payload["observable_state"],
        }

    def _request_response_row(self, item: RequestResponseRecord) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "recording_id": payload["recording_id"],
            "page_stage_id": payload["page_stage_id"],
            "request_method": payload["request_method"],
            "request_url": payload["request_url"],
            "request_headers_json": payload["request_headers"],
            "request_body_blob_key": payload["request_body_blob_key"],
            "response_status": payload["response_status"],
            "response_headers_json": payload["response_headers"],
            "response_body_blob_key": payload["response_body_blob_key"],
            "requested_at": item.requested_at,
            "finished_at": item.finished_at,
            "duration_ms": payload["duration_ms"],
            "failure_reason": payload["failure_reason"],
        }

    def _session_state_row(self, item: SessionStateSnapshot) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "recording_id": payload["recording_id"],
            "browser_session_id": payload["browser_session_id"],
            "page_stage_id": payload["page_stage_id"],
            "request_id": payload["request_id"],
            "captured_at": item.captured_at,
            "cookie_summary_json": payload["cookie_summary"],
            "storage_summary_json": payload["storage_summary"],
        }

    def _file_transfer_row(self, item: FileTransferRecord) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "recording_id": payload["recording_id"],
            "related_request_id": payload["related_request_id"],
            "direction": payload["direction"],
            "file_name": payload["file_name"],
            "stored_file_blob_key": None,
            "occurred_at": item.occurred_at,
            "source_path_summary": payload["source_path_summary"],
            "target_path_summary": payload["target_path_summary"],
            "notes": payload["notes"],
        }

    def _metadata_draft_row(self, item: MetadataDraft) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "version": payload["version"],
            "previous_version": payload["previous_version"],
            "recording_id": payload["recording_id"],
            "candidate_request_ids_json": payload["candidate_request_ids"],
            "parameter_suggestions_json": payload["parameter_suggestions"],
            "action_fragment_suggestions_json": payload["action_fragment_suggestions"],
            "analysis_notes": payload["analysis_notes"],
            "generated_at": payload["generated_at"],
        }

    def _reviewed_metadata_row(self, item: ReviewedMetadata) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "version": payload["version"],
            "previous_version": payload["previous_version"],
            "recording_id": payload["recording_id"],
            "reviewer": payload["reviewer"],
            "source_draft_id": payload["source_draft_id"],
            "source_draft_version": payload["source_draft_version"],
            "key_request_ids_json": payload["key_request_ids"],
            "noise_request_ids_json": payload["noise_request_ids"],
            "field_descriptions_json": payload["field_descriptions"],
            "parameter_source_map_json": payload["parameter_source_map"],
            "action_stage_ids_json": payload["action_stage_ids"],
            "risk_flags_json": payload["risk_flags"],
            "reviewed_at": payload["reviewed_at"],
        }

    def _load_browser_session(self, row) -> BrowserSession:  # type: ignore[no-untyped-def]
        return BrowserSession(
            id=row["id"],
            profile_id=row["profile_id"],
            status=row["status"],
            login_site_summaries=row["login_site_summaries_json"],
            created_at=_ensure_utc(row["created_at"]),
            last_activity_at=_ensure_utc(row["last_activity_at"]),
        )

    def _load_recording(self, row) -> Recording:  # type: ignore[no-untyped-def]
        return Recording(
            id=row["id"],
            name=row["name"],
            start_url=row["start_url"],
            browser_session_id=row["browser_session_id"],
            status=row["status"],
            created_at=_ensure_utc(row["created_at"]),
            started_at=_ensure_utc(row["started_at"]),
            ended_at=_ensure_utc(row["ended_at"]),
            generated_action_macro_id=row["generated_action_macro_id"],
        )

    def _load_page_stage(self, row) -> PageStage:  # type: ignore[no-untyped-def]
        return PageStage(
            id=row["id"],
            recording_id=row["recording_id"],
            url=row["url"],
            name=row["name"],
            started_at=_ensure_utc(row["started_at"]),
            ended_at=_ensure_utc(row["ended_at"]),
            related_request_ids=row["related_request_ids_json"],
            wait_points=row["wait_points_json"],
            observable_state=row["observable_state_json"],
        )

    def _load_request_response(self, row) -> RequestResponseRecord:  # type: ignore[no-untyped-def]
        return RequestResponseRecord(
            id=row["id"],
            recording_id=row["recording_id"],
            page_stage_id=row["page_stage_id"],
            request_method=row["request_method"],
            request_url=row["request_url"],
            requested_at=_ensure_utc(row["requested_at"]),
            request_headers=_load_headers(row["request_headers_json"]),
            request_body_blob_key=row["request_body_blob_key"],
            response_status=row["response_status"],
            response_headers=_load_headers(row["response_headers_json"]),
            response_body_blob_key=row["response_body_blob_key"],
            finished_at=_ensure_utc(row["finished_at"]),
            duration_ms=row["duration_ms"],
            failure_reason=row["failure_reason"],
        )

    def _load_session_state_snapshot(self, row) -> SessionStateSnapshot:  # type: ignore[no-untyped-def]
        return SessionStateSnapshot(
            id=row["id"],
            recording_id=row["recording_id"],
            browser_session_id=row["browser_session_id"],
            page_stage_id=row["page_stage_id"],
            request_id=row["request_id"],
            captured_at=_ensure_utc(row["captured_at"]),
            cookie_summary=row["cookie_summary_json"],
            storage_summary=row["storage_summary_json"],
        )

    def _load_file_transfer(self, row) -> FileTransferRecord:  # type: ignore[no-untyped-def]
        return FileTransferRecord(
            id=row["id"],
            recording_id=row["recording_id"],
            direction=row["direction"],
            file_name=row["file_name"],
            related_request_id=row["related_request_id"],
            occurred_at=_ensure_utc(row["occurred_at"]),
            source_path_summary=row["source_path_summary"],
            target_path_summary=row["target_path_summary"],
            notes=row["notes"],
        )

    def _load_metadata_draft(self, row) -> MetadataDraft:  # type: ignore[no-untyped-def]
        return MetadataDraft(
            id=row["id"],
            version=row["version"],
            previous_version=row["previous_version"],
            recording_id=row["recording_id"],
            candidate_request_ids=row["candidate_request_ids_json"],
            parameter_suggestions=row["parameter_suggestions_json"],
            action_fragment_suggestions=row["action_fragment_suggestions_json"],
            analysis_notes=row["analysis_notes"],
            generated_at=_ensure_utc(row["generated_at"]),
        )

    def _load_reviewed_metadata(self, row) -> ReviewedMetadata:  # type: ignore[no-untyped-def]
        return ReviewedMetadata(
            id=row["id"],
            version=row["version"],
            previous_version=row["previous_version"],
            recording_id=row["recording_id"],
            reviewer=row["reviewer"],
            source_draft_id=row["source_draft_id"],
            source_draft_version=row["source_draft_version"],
            key_request_ids=row["key_request_ids_json"],
            noise_request_ids=row["noise_request_ids_json"],
            field_descriptions=row["field_descriptions_json"],
            parameter_source_map=row["parameter_source_map_json"],
            action_stage_ids=row["action_stage_ids_json"],
            risk_flags=row["risk_flags_json"],
            reviewed_at=_ensure_utc(row["reviewed_at"]),
        )


def _load_headers(items: list[dict[str, str]]) -> list[HttpHeader]:
    return [HttpHeader(**item) for item in items]


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value

    return value.replace(tzinfo=UTC)
