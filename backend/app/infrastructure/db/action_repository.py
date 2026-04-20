from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker

from app.action.domain import ActionKind, ActionMacro, ActionStep, ParameterDefinition
from app.infrastructure.db.schema import action_macro, parameter_definition
from app.infrastructure.storage.storage_bootstrap import StorageLayout


class SqliteActionMacroRepository:
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
        item: ActionMacro,
        *,
        session: Session | None = None,
        write_files: bool = True,
    ) -> None:
        if session is None:
            with self._session_factory.begin() as managed_session:
                self._save_in_session(managed_session, item)
        else:
            self._save_in_session(session, item)

        if write_files:
            self._write_action_file(item)

    def _save_in_session(self, session: Session, item: ActionMacro) -> None:
        session.execute(
            delete(action_macro).where(
                action_macro.c.id == item.id,
                action_macro.c.version == item.version,
            )
        )
        session.execute(insert(action_macro).values(self._action_macro_row(item)))
        session.execute(
            delete(parameter_definition).where(
                parameter_definition.c.owner_kind == ActionKind.ACTION_MACRO.value,
                parameter_definition.c.action_id == item.id,
                parameter_definition.c.action_version == item.version,
            )
        )
        if item.parameter_definitions:
            session.execute(
                insert(parameter_definition),
                [
                    self._parameter_definition_row(definition, item.version)
                    for definition in item.parameter_definitions
                ],
            )

    def get(self, action_id: str, version: int | None = None) -> ActionMacro | None:
        with self._session_factory() as session:
            statement = select(action_macro).where(action_macro.c.id == action_id)
            if version is None:
                statement = statement.order_by(action_macro.c.version.desc())
            else:
                statement = statement.where(action_macro.c.version == version)
            row = session.execute(statement).mappings().first()
            if row is None:
                return None
            return self._load_action_macro(session, row)

    def list(self) -> tuple[ActionMacro, ...]:
        with self._session_factory() as session:
            rows = session.execute(
                select(action_macro).order_by(
                    action_macro.c.created_at.desc(),
                    action_macro.c.version.desc(),
                )
            ).mappings()
            latest_by_id: dict[str, ActionMacro] = {}
            for row in rows:
                if row["id"] in latest_by_id:
                    continue
                latest_by_id[row["id"]] = self._load_action_macro(session, row)
            return tuple(latest_by_id.values())

    def _action_macro_row(self, item: ActionMacro) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "version": payload["version"],
            "previous_version": payload["previous_version"],
            "recording_id": payload["recording_id"],
            "name": payload["name"],
            "source_reviewed_metadata_id": payload["source_reviewed_metadata_id"],
            "source_reviewed_metadata_version": payload["source_reviewed_metadata_version"],
            "description": payload["description"],
            "steps_json": payload["steps"],
            "required_page_stage_ids_json": payload["required_page_stage_ids"],
            "session_requirements_json": payload["session_requirements"],
            "created_at": payload["created_at"],
        }

    def _parameter_definition_row(
        self,
        item: ParameterDefinition,
        action_version: int,
    ) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "owner_kind": payload["owner_kind"],
            "action_id": payload["action_id"],
            "action_version": action_version,
            "name": payload["name"],
            "parameter_kind": payload["parameter_kind"],
            "required": payload["required"],
            "default_value_json": payload["default_value"],
            "injection_target": payload["injection_target"],
            "description": payload["description"],
        }

    def _load_action_macro(self, session: Session, row) -> ActionMacro:  # type: ignore[no-untyped-def]
        parameter_rows = session.execute(
            select(parameter_definition)
            .where(
                parameter_definition.c.owner_kind == ActionKind.ACTION_MACRO.value,
                parameter_definition.c.action_id == row["id"],
                parameter_definition.c.action_version == row["version"],
            )
            .order_by(parameter_definition.c.name.asc())
        ).mappings()
        return ActionMacro(
            id=row["id"],
            version=row["version"],
            previous_version=row["previous_version"],
            recording_id=row["recording_id"],
            name=row["name"],
            source_reviewed_metadata_id=row["source_reviewed_metadata_id"],
            source_reviewed_metadata_version=row["source_reviewed_metadata_version"],
            description=row["description"],
            steps=[ActionStep(**item) for item in row["steps_json"]],
            required_page_stage_ids=row["required_page_stage_ids_json"],
            parameter_definitions=[
                ParameterDefinition(
                    id=item["id"],
                    owner_kind=item["owner_kind"],
                    action_id=item["action_id"],
                    name=item["name"],
                    parameter_kind=item["parameter_kind"],
                    required=item["required"],
                    default_value=item["default_value_json"],
                    injection_target=item["injection_target"],
                    description=item["description"],
                )
                for item in parameter_rows
            ],
            session_requirements=row["session_requirements_json"],
            created_at=_ensure_utc(row["created_at"]),
        )

    def _write_action_file(self, item: ActionMacro) -> None:
        path = self._storage_layout.action_macro_version_path(item.id, item.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(item.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value

    return value.replace(tzinfo=UTC)
