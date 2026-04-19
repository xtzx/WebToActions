"""stage2 storage baseline

Revision ID: 20260419_0001
Revises:
Create Date: 2026-04-19 15:45:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision = "20260419_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "browser_session",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("profile_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("login_site_summaries_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_browser_session"),
    )
    op.create_table(
        "recording",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("start_url", sa.Text(), nullable=False),
        sa.Column("browser_session_id", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_action_macro_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["browser_session_id"],
            ["browser_session.id"],
            name="fk_recording_browser_session_id_browser_session",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recording"),
    )
    op.create_table(
        "page_stage",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("recording_id", sa.String(length=128), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("related_request_ids_json", sa.JSON(), nullable=False),
        sa.Column("wait_points_json", sa.JSON(), nullable=False),
        sa.Column("observable_state_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.id"],
            name="fk_page_stage_recording_id_recording",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_page_stage"),
    )
    op.create_table(
        "request_response_record",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("recording_id", sa.String(length=128), nullable=False),
        sa.Column("page_stage_id", sa.String(length=128), nullable=True),
        sa.Column("request_method", sa.String(length=16), nullable=False),
        sa.Column("request_url", sa.Text(), nullable=False),
        sa.Column("request_headers_json", sa.JSON(), nullable=False),
        sa.Column("request_body_blob_key", sa.Text(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_headers_json", sa.JSON(), nullable=False),
        sa.Column("response_body_blob_key", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["page_stage_id"],
            ["page_stage.id"],
            name="fk_request_response_record_page_stage_id_page_stage",
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.id"],
            name="fk_request_response_record_recording_id_recording",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_request_response_record"),
    )
    op.create_table(
        "session_state_snapshot",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("recording_id", sa.String(length=128), nullable=False),
        sa.Column("browser_session_id", sa.String(length=128), nullable=False),
        sa.Column("page_stage_id", sa.String(length=128), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cookie_summary_json", sa.JSON(), nullable=False),
        sa.Column("storage_summary_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["browser_session_id"],
            ["browser_session.id"],
            name="fk_session_state_snapshot_browser_session_id_browser_session",
        ),
        sa.ForeignKeyConstraint(
            ["page_stage_id"],
            ["page_stage.id"],
            name="fk_session_state_snapshot_page_stage_id_page_stage",
        ),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.id"],
            name="fk_session_state_snapshot_recording_id_recording",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["request_response_record.id"],
            name="fk_session_state_snapshot_request_id_request_response_record",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_session_state_snapshot"),
    )
    op.create_table(
        "file_transfer_record",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("recording_id", sa.String(length=128), nullable=False),
        sa.Column("related_request_id", sa.String(length=128), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("file_name", sa.Text(), nullable=False),
        sa.Column("stored_file_blob_key", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_path_summary", sa.Text(), nullable=True),
        sa.Column("target_path_summary", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.id"],
            name="fk_file_transfer_record_recording_id_recording",
        ),
        sa.ForeignKeyConstraint(
            ["related_request_id"],
            ["request_response_record.id"],
            name="fk_file_transfer_record_related_request_id_request_response_record",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_file_transfer_record"),
    )
    op.create_table(
        "metadata_draft",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version", sa.Integer(), nullable=True),
        sa.Column("recording_id", sa.String(length=128), nullable=False),
        sa.Column("candidate_request_ids_json", sa.JSON(), nullable=False),
        sa.Column("parameter_suggestions_json", sa.JSON(), nullable=False),
        sa.Column("action_fragment_suggestions_json", sa.JSON(), nullable=False),
        sa.Column("analysis_notes", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.id"],
            name="fk_metadata_draft_recording_id_recording",
        ),
        sa.PrimaryKeyConstraint("id", "version", name="pk_metadata_draft"),
    )
    op.create_table(
        "reviewed_metadata",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version", sa.Integer(), nullable=True),
        sa.Column("recording_id", sa.String(length=128), nullable=False),
        sa.Column("reviewer", sa.String(length=255), nullable=False),
        sa.Column("source_draft_id", sa.String(length=128), nullable=False),
        sa.Column("source_draft_version", sa.Integer(), nullable=False),
        sa.Column("key_request_ids_json", sa.JSON(), nullable=False),
        sa.Column("field_descriptions_json", sa.JSON(), nullable=False),
        sa.Column("parameter_source_map_json", sa.JSON(), nullable=False),
        sa.Column("action_stage_ids_json", sa.JSON(), nullable=False),
        sa.Column("risk_flags_json", sa.JSON(), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.id"],
            name="fk_reviewed_metadata_recording_id_recording",
        ),
        sa.ForeignKeyConstraint(
            ["source_draft_id", "source_draft_version"],
            ["metadata_draft.id", "metadata_draft.version"],
            name="fk_reviewed_metadata_source_draft_id_metadata_draft",
        ),
        sa.PrimaryKeyConstraint("id", "version", name="pk_reviewed_metadata"),
    )
    op.create_table(
        "action_macro",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version", sa.Integer(), nullable=True),
        sa.Column("recording_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_reviewed_metadata_id", sa.String(length=128), nullable=False),
        sa.Column("source_reviewed_metadata_version", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps_json", sa.JSON(), nullable=False),
        sa.Column("required_page_stage_ids_json", sa.JSON(), nullable=False),
        sa.Column("session_requirements_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["recording_id"],
            ["recording.id"],
            name="fk_action_macro_recording_id_recording",
        ),
        sa.ForeignKeyConstraint(
            ["source_reviewed_metadata_id", "source_reviewed_metadata_version"],
            ["reviewed_metadata.id", "reviewed_metadata.version"],
            name="fk_action_macro_source_reviewed_metadata_id_reviewed_metadata",
        ),
        sa.PrimaryKeyConstraint("id", "version", name="pk_action_macro"),
    )
    op.create_table(
        "business_action",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("source_action_macro_id", sa.String(length=128), nullable=False),
        sa.Column("source_action_macro_version", sa.Integer(), nullable=False),
        sa.Column("business_steps_json", sa.JSON(), nullable=False),
        sa.Column("outputs_json", sa.JSON(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_action_macro_id", "source_action_macro_version"],
            ["action_macro.id", "action_macro.version"],
            name="fk_business_action_source_action_macro_id_action_macro",
        ),
        sa.PrimaryKeyConstraint("id", "version", name="pk_business_action"),
    )
    op.create_table(
        "parameter_definition",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("owner_kind", sa.String(length=32), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=False),
        sa.Column("action_version", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parameter_kind", sa.String(length=32), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("default_value_json", sa.JSON(), nullable=True),
        sa.Column("injection_target", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", "owner_kind", name="pk_parameter_definition"),
    )
    op.create_table(
        "execution_run",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("action_kind", sa.String(length=32), nullable=False),
        sa.Column("action_id", sa.String(length=128), nullable=False),
        sa.Column("action_version", sa.Integer(), nullable=False),
        sa.Column("browser_session_id", sa.String(length=128), nullable=False),
        sa.Column("parameters_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("step_logs_blob_key", sa.Text(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("diagnostics_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["browser_session_id"],
            ["browser_session.id"],
            name="fk_execution_run_browser_session_id_browser_session",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_execution_run"),
    )
    op.create_table(
        "export_bundle",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("previous_version", sa.Integer(), nullable=True),
        sa.Column("export_scope", sa.String(length=32), nullable=False),
        sa.Column("package_format_version", sa.String(length=32), nullable=False),
        sa.Column("recording_ids_json", sa.JSON(), nullable=False),
        sa.Column("reviewed_metadata_refs_json", sa.JSON(), nullable=False),
        sa.Column("action_macro_refs_json", sa.JSON(), nullable=False),
        sa.Column("business_action_refs_json", sa.JSON(), nullable=False),
        sa.Column("file_manifest_json", sa.JSON(), nullable=False),
        sa.Column("bundle_blob_key", sa.Text(), nullable=True),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", "version", name="pk_export_bundle"),
    )

    op.create_index(
        "ix_recording_browser_session_status",
        "recording",
        ["browser_session_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_page_stage_recording_started_at",
        "page_stage",
        ["recording_id", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_request_response_record_recording_requested_at",
        "request_response_record",
        ["recording_id", "requested_at"],
        unique=False,
    )
    op.create_index(
        "ix_session_state_snapshot_recording_captured_at",
        "session_state_snapshot",
        ["recording_id", "captured_at"],
        unique=False,
    )
    op.create_index(
        "ix_file_transfer_record_recording_occurred_at",
        "file_transfer_record",
        ["recording_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_metadata_draft_recording_version",
        "metadata_draft",
        ["recording_id", "version"],
        unique=False,
    )
    op.create_index(
        "ix_reviewed_metadata_recording_version",
        "reviewed_metadata",
        ["recording_id", "version"],
        unique=False,
    )
    op.create_index(
        "ix_action_macro_recording_version",
        "action_macro",
        ["recording_id", "version"],
        unique=False,
    )
    op.create_index(
        "ix_parameter_definition_owner_action",
        "parameter_definition",
        ["owner_kind", "action_id", "action_version"],
        unique=False,
    )
    op.create_index(
        "ix_execution_run_action_ref",
        "execution_run",
        ["action_kind", "action_id", "action_version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_execution_run_action_ref", table_name="execution_run")
    op.drop_index("ix_parameter_definition_owner_action", table_name="parameter_definition")
    op.drop_index("ix_action_macro_recording_version", table_name="action_macro")
    op.drop_index("ix_reviewed_metadata_recording_version", table_name="reviewed_metadata")
    op.drop_index("ix_metadata_draft_recording_version", table_name="metadata_draft")
    op.drop_index(
        "ix_file_transfer_record_recording_occurred_at",
        table_name="file_transfer_record",
    )
    op.drop_index(
        "ix_session_state_snapshot_recording_captured_at",
        table_name="session_state_snapshot",
    )
    op.drop_index(
        "ix_request_response_record_recording_requested_at",
        table_name="request_response_record",
    )
    op.drop_index("ix_page_stage_recording_started_at", table_name="page_stage")
    op.drop_index("ix_recording_browser_session_status", table_name="recording")

    op.drop_table("export_bundle")
    op.drop_table("execution_run")
    op.drop_table("parameter_definition")
    op.drop_table("business_action")
    op.drop_table("action_macro")
    op.drop_table("reviewed_metadata")
    op.drop_table("metadata_draft")
    op.drop_table("file_transfer_record")
    op.drop_table("session_state_snapshot")
    op.drop_table("request_response_record")
    op.drop_table("page_stage")
    op.drop_table("recording")
    op.drop_table("browser_session")
