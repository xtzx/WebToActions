"""recording scoped evidence keys

Revision ID: 20260420_0003
Revises: 20260419_0002
Create Date: 2026-04-20 14:20:00
"""

from collections.abc import Sequence

from alembic import op


revision = "20260420_0003"
down_revision = "20260419_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _set_session_state_snapshot_primary_key(["recording_id", "id"], drop_legacy_fks=True)
    _set_file_transfer_record_primary_key(["recording_id", "id"], drop_legacy_fk=True)
    _set_request_response_record_primary_key(["recording_id", "id"], drop_legacy_fk=True)
    _set_page_stage_primary_key(["recording_id", "id"])

    _create_request_response_record_page_stage_fk(
        ["recording_id", "page_stage_id"],
        ["recording_id", "id"],
    )
    _create_session_state_snapshot_page_stage_fk(
        ["recording_id", "page_stage_id"],
        ["recording_id", "id"],
    )
    _create_session_state_snapshot_request_fk(
        ["recording_id", "request_id"],
        ["recording_id", "id"],
    )
    _create_file_transfer_record_request_fk(
        ["recording_id", "related_request_id"],
        ["recording_id", "id"],
    )


def downgrade() -> None:
    _drop_file_transfer_record_request_fk(
        "fk_file_transfer_record_recording_id_request_response_record"
    )
    _drop_session_state_snapshot_request_fk(
        "fk_session_state_snapshot_recording_id_request_response_record"
    )
    _drop_session_state_snapshot_page_stage_fk(
        "fk_session_state_snapshot_recording_id_page_stage"
    )
    _drop_request_response_record_page_stage_fk(
        "fk_request_response_record_recording_id_page_stage"
    )

    _set_session_state_snapshot_primary_key(["id"], drop_legacy_fks=False)
    _set_file_transfer_record_primary_key(["id"], drop_legacy_fk=False)
    _set_request_response_record_primary_key(["id"], drop_legacy_fk=False)
    _set_page_stage_primary_key(["id"])

    _create_request_response_record_page_stage_fk(["page_stage_id"], ["id"])
    _create_session_state_snapshot_page_stage_fk(["page_stage_id"], ["id"])
    _create_session_state_snapshot_request_fk(["request_id"], ["id"])
    _create_file_transfer_record_request_fk(["related_request_id"], ["id"])


def _set_page_stage_primary_key(columns: list[str]) -> None:
    with op.batch_alter_table("page_stage", recreate="always") as batch_op:
        batch_op.drop_constraint("pk_page_stage", type_="primary")
        batch_op.create_primary_key("pk_page_stage", columns)


def _set_request_response_record_primary_key(
    columns: list[str],
    *,
    drop_legacy_fk: bool,
) -> None:
    with op.batch_alter_table("request_response_record", recreate="always") as batch_op:
        if drop_legacy_fk:
            batch_op.drop_constraint(
                "fk_request_response_record_page_stage_id_page_stage",
                type_="foreignkey",
            )
        batch_op.drop_constraint("pk_request_response_record", type_="primary")
        batch_op.create_primary_key("pk_request_response_record", columns)


def _set_session_state_snapshot_primary_key(
    columns: list[str],
    *,
    drop_legacy_fks: bool,
) -> None:
    with op.batch_alter_table("session_state_snapshot", recreate="always") as batch_op:
        if drop_legacy_fks:
            batch_op.drop_constraint(
                "fk_session_state_snapshot_page_stage_id_page_stage",
                type_="foreignkey",
            )
            batch_op.drop_constraint(
                "fk_session_state_snapshot_request_id_request_response_record",
                type_="foreignkey",
            )
        batch_op.drop_constraint("pk_session_state_snapshot", type_="primary")
        batch_op.create_primary_key("pk_session_state_snapshot", columns)


def _set_file_transfer_record_primary_key(
    columns: list[str],
    *,
    drop_legacy_fk: bool,
) -> None:
    with op.batch_alter_table("file_transfer_record", recreate="always") as batch_op:
        if drop_legacy_fk:
            batch_op.drop_constraint(
                "fk_file_transfer_record_related_request_id_request_response_record",
                type_="foreignkey",
            )
        batch_op.drop_constraint("pk_file_transfer_record", type_="primary")
        batch_op.create_primary_key("pk_file_transfer_record", columns)


def _create_request_response_record_page_stage_fk(
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    with op.batch_alter_table("request_response_record", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_request_response_record_recording_id_page_stage",
            "page_stage",
            local_cols,
            remote_cols,
        )


def _drop_request_response_record_page_stage_fk(name: str) -> None:
    with op.batch_alter_table("request_response_record", recreate="always") as batch_op:
        batch_op.drop_constraint(name, type_="foreignkey")


def _create_session_state_snapshot_page_stage_fk(
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    with op.batch_alter_table("session_state_snapshot", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_session_state_snapshot_recording_id_page_stage",
            "page_stage",
            local_cols,
            remote_cols,
        )


def _drop_session_state_snapshot_page_stage_fk(name: str) -> None:
    with op.batch_alter_table("session_state_snapshot", recreate="always") as batch_op:
        batch_op.drop_constraint(name, type_="foreignkey")


def _create_session_state_snapshot_request_fk(
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    with op.batch_alter_table("session_state_snapshot", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_session_state_snapshot_recording_id_request_response_record",
            "request_response_record",
            local_cols,
            remote_cols,
        )


def _drop_session_state_snapshot_request_fk(name: str) -> None:
    with op.batch_alter_table("session_state_snapshot", recreate="always") as batch_op:
        batch_op.drop_constraint(name, type_="foreignkey")


def _create_file_transfer_record_request_fk(
    local_cols: list[str],
    remote_cols: list[str],
) -> None:
    with op.batch_alter_table("file_transfer_record", recreate="always") as batch_op:
        batch_op.create_foreign_key(
            "fk_file_transfer_record_recording_id_request_response_record",
            "request_response_record",
            local_cols,
            remote_cols,
        )


def _drop_file_transfer_record_request_fk(name: str) -> None:
    with op.batch_alter_table("file_transfer_record", recreate="always") as batch_op:
        batch_op.drop_constraint(name, type_="foreignkey")


def _unused(_: Sequence[object]) -> None:
    return None
