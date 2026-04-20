from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import PurePosixPath

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.domain_model import FrozenDict, FrozenList
from app.execution.domain.execution_run import ExecutionRun
from app.infrastructure.db.schema import execution_run
from app.infrastructure.storage.storage_bootstrap import StorageLayout


class SqliteExecutionRunRepository:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        storage_layout: StorageLayout,
    ) -> None:
        self._session_factory = session_factory
        self._storage_layout = storage_layout

    def save(
        self,
        item: ExecutionRun,
        *,
        session: Session | None = None,
        write_files: bool = True,
    ) -> None:
        step_logs_blob_key = self._write_step_logs(item)
        if session is None:
            with self._session_factory.begin() as managed_session:
                self._save_in_session(managed_session, item, step_logs_blob_key)
        else:
            self._save_in_session(session, item, step_logs_blob_key)
        if write_files:
            self._write_summary(item)

    def _save_in_session(
        self,
        session: Session,
        item: ExecutionRun,
        step_logs_blob_key: str,
    ) -> None:
        session.execute(delete(execution_run).where(execution_run.c.id == item.id))
        session.execute(
            insert(execution_run).values(
                {
                    "id": item.id,
                    "action_kind": item.action_kind.value,
                    "action_id": item.action_id,
                    "action_version": item.action_version,
                    "browser_session_id": item.browser_session_id,
                    "parameters_snapshot_json": _to_plain_json(item.parameters_snapshot),
                    "status": item.status.value,
                    "created_at": item.created_at,
                    "started_at": item.started_at,
                    "ended_at": item.ended_at,
                    "step_logs_blob_key": step_logs_blob_key,
                    "failure_reason": item.failure_reason,
                    "diagnostics_json": _to_plain_json(item.diagnostics),
                }
            )
        )

    def get(self, execution_id: str) -> ExecutionRun | None:
        with self._session_factory() as session:
            row = session.execute(
                select(execution_run).where(execution_run.c.id == execution_id)
            ).mappings().first()
            if row is None:
                return None
            return self._load_execution_run(row)

    def list(self) -> tuple[ExecutionRun, ...]:
        with self._session_factory() as session:
            rows = session.execute(
                select(execution_run).order_by(execution_run.c.created_at.desc())
            ).mappings()
            return tuple(self._load_execution_run(row) for row in rows)

    def _load_execution_run(self, row) -> ExecutionRun:  # type: ignore[no-untyped-def]
        return ExecutionRun(
            id=row["id"],
            action_kind=row["action_kind"],
            action_id=row["action_id"],
            action_version=row["action_version"],
            browser_session_id=row["browser_session_id"],
            parameters_snapshot=row["parameters_snapshot_json"],
            status=row["status"],
            created_at=_ensure_utc(row["created_at"]),
            started_at=_ensure_utc(row["started_at"]),
            ended_at=_ensure_utc(row["ended_at"]),
            step_logs=self._read_step_logs(row["step_logs_blob_key"]),
            failure_reason=row["failure_reason"],
            diagnostics=row["diagnostics_json"],
        )

    def _write_step_logs(self, item: ExecutionRun) -> str:
        logs_dir = self._storage_layout.execution_run_logs_dir(item.id)
        logs_dir.mkdir(parents=True, exist_ok=True)
        logs_path = logs_dir / "step-logs.json"
        logs_path.write_text(
            json.dumps(list(item.step_logs), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(PurePosixPath("runs") / f"run_{item.id}" / "logs" / "step-logs.json")

    def _read_step_logs(self, blob_key: str | None) -> list[str]:
        if not blob_key:
            return []
        path = self._storage_layout.root / blob_key
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_summary(self, item: ExecutionRun) -> None:
        summary_path = self._storage_layout.execution_run_summary_path(item.id)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(
            json.dumps(item.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value

    return value.replace(tzinfo=UTC)


def _to_plain_json(value):  # type: ignore[no-untyped-def]
    if isinstance(value, FrozenList):
        return [_to_plain_json(item) for item in value]
    if isinstance(value, (list, tuple)):
        return [_to_plain_json(item) for item in value]
    if isinstance(value, FrozenDict):
        return {key: _to_plain_json(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {key: _to_plain_json(item) for key, item in value.items()}
    return value
