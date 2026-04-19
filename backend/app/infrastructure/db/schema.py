from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)


metadata = MetaData(
    naming_convention={
        "ix": "ix_%(table_name)s_%(column_0_name)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


browser_session = Table(
    "browser_session",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("profile_id", String(128), nullable=False),
    Column("status", String(32), nullable=False),
    Column("login_site_summaries_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_activity_at", DateTime(timezone=True), nullable=False),
)


recording = Table(
    "recording",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("start_url", Text, nullable=False),
    Column("browser_session_id", String(128), ForeignKey("browser_session.id"), nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("ended_at", DateTime(timezone=True)),
    Column("generated_action_macro_id", String(128)),
)


page_stage = Table(
    "page_stage",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("recording_id", String(128), ForeignKey("recording.id"), nullable=False),
    Column("url", Text, nullable=False),
    Column("name", String(255), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("ended_at", DateTime(timezone=True)),
    Column("related_request_ids_json", JSON, nullable=False),
    Column("wait_points_json", JSON, nullable=False),
    Column("observable_state_json", JSON, nullable=False),
)


request_response_record = Table(
    "request_response_record",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("recording_id", String(128), ForeignKey("recording.id"), nullable=False),
    Column("page_stage_id", String(128), ForeignKey("page_stage.id")),
    Column("request_method", String(16), nullable=False),
    Column("request_url", Text, nullable=False),
    Column("request_headers_json", JSON, nullable=False),
    Column("request_body_blob_key", Text),
    Column("response_status", Integer),
    Column("response_headers_json", JSON, nullable=False),
    Column("response_body_blob_key", Text),
    Column("requested_at", DateTime(timezone=True), nullable=False),
    Column("finished_at", DateTime(timezone=True)),
    Column("duration_ms", Integer),
    Column("failure_reason", Text),
)


session_state_snapshot = Table(
    "session_state_snapshot",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("recording_id", String(128), ForeignKey("recording.id"), nullable=False),
    Column("browser_session_id", String(128), ForeignKey("browser_session.id"), nullable=False),
    Column("page_stage_id", String(128), ForeignKey("page_stage.id")),
    Column("request_id", String(128), ForeignKey("request_response_record.id")),
    Column("captured_at", DateTime(timezone=True), nullable=False),
    Column("cookie_summary_json", JSON, nullable=False),
    Column("storage_summary_json", JSON, nullable=False),
)


file_transfer_record = Table(
    "file_transfer_record",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("recording_id", String(128), ForeignKey("recording.id"), nullable=False),
    Column("related_request_id", String(128), ForeignKey("request_response_record.id")),
    Column("direction", String(16), nullable=False),
    Column("file_name", Text, nullable=False),
    Column("stored_file_blob_key", Text),
    Column("occurred_at", DateTime(timezone=True), nullable=False),
    Column("source_path_summary", Text),
    Column("target_path_summary", Text),
    Column("notes", Text),
)


metadata_draft = Table(
    "metadata_draft",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("previous_version", Integer),
    Column("recording_id", String(128), ForeignKey("recording.id"), nullable=False),
    Column("candidate_request_ids_json", JSON, nullable=False),
    Column("parameter_suggestions_json", JSON, nullable=False),
    Column("action_fragment_suggestions_json", JSON, nullable=False),
    Column("analysis_notes", Text),
    Column("generated_at", DateTime(timezone=True), nullable=False),
)


reviewed_metadata = Table(
    "reviewed_metadata",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("previous_version", Integer),
    Column("recording_id", String(128), ForeignKey("recording.id"), nullable=False),
    Column("reviewer", String(255), nullable=False),
    Column("source_draft_id", String(128), nullable=False),
    Column("source_draft_version", Integer, nullable=False),
    Column("key_request_ids_json", JSON, nullable=False),
    Column("noise_request_ids_json", JSON, nullable=False),
    Column("field_descriptions_json", JSON, nullable=False),
    Column("parameter_source_map_json", JSON, nullable=False),
    Column("action_stage_ids_json", JSON, nullable=False),
    Column("risk_flags_json", JSON, nullable=False),
    Column("reviewed_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["source_draft_id", "source_draft_version"],
        ["metadata_draft.id", "metadata_draft.version"],
    ),
)


action_macro = Table(
    "action_macro",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("previous_version", Integer),
    Column("recording_id", String(128), ForeignKey("recording.id"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("source_reviewed_metadata_id", String(128), nullable=False),
    Column("source_reviewed_metadata_version", Integer, nullable=False),
    Column("description", Text),
    Column("steps_json", JSON, nullable=False),
    Column("required_page_stage_ids_json", JSON, nullable=False),
    Column("session_requirements_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["source_reviewed_metadata_id", "source_reviewed_metadata_version"],
        ["reviewed_metadata.id", "reviewed_metadata.version"],
    ),
)


business_action = Table(
    "business_action",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("previous_version", Integer),
    Column("name", String(255), nullable=False),
    Column("source_action_macro_id", String(128), nullable=False),
    Column("source_action_macro_version", Integer, nullable=False),
    Column("business_steps_json", JSON, nullable=False),
    Column("outputs_json", JSON, nullable=False),
    Column("constraints_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    ForeignKeyConstraint(
        ["source_action_macro_id", "source_action_macro_version"],
        ["action_macro.id", "action_macro.version"],
    ),
)


parameter_definition = Table(
    "parameter_definition",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("owner_kind", String(32), primary_key=True),
    Column("action_id", String(128), nullable=False),
    Column("action_version", Integer, nullable=False),
    Column("name", String(255), nullable=False),
    Column("parameter_kind", String(32), nullable=False),
    Column("required", Boolean, nullable=False),
    Column("default_value_json", JSON),
    Column("injection_target", Text, nullable=False),
    Column("description", Text),
)


execution_run = Table(
    "execution_run",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("action_kind", String(32), nullable=False),
    Column("action_id", String(128), nullable=False),
    Column("action_version", Integer, nullable=False),
    Column("browser_session_id", String(128), ForeignKey("browser_session.id"), nullable=False),
    Column("parameters_snapshot_json", JSON, nullable=False),
    Column("status", String(32), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("ended_at", DateTime(timezone=True)),
    Column("step_logs_blob_key", Text),
    Column("failure_reason", Text),
    Column("diagnostics_json", JSON, nullable=False),
)


export_bundle = Table(
    "export_bundle",
    metadata,
    Column("id", String(128), primary_key=True),
    Column("version", Integer, primary_key=True),
    Column("previous_version", Integer),
    Column("export_scope", String(32), nullable=False),
    Column("package_format_version", String(32), nullable=False),
    Column("recording_ids_json", JSON, nullable=False),
    Column("reviewed_metadata_refs_json", JSON, nullable=False),
    Column("action_macro_refs_json", JSON, nullable=False),
    Column("business_action_refs_json", JSON, nullable=False),
    Column("file_manifest_json", JSON, nullable=False),
    Column("bundle_blob_key", Text),
    Column("exported_at", DateTime(timezone=True), nullable=False),
)


Index("ix_recording_browser_session_status", recording.c.browser_session_id, recording.c.status)
Index("ix_page_stage_recording_started_at", page_stage.c.recording_id, page_stage.c.started_at)
Index(
    "ix_request_response_record_recording_requested_at",
    request_response_record.c.recording_id,
    request_response_record.c.requested_at,
)
Index(
    "ix_session_state_snapshot_recording_captured_at",
    session_state_snapshot.c.recording_id,
    session_state_snapshot.c.captured_at,
)
Index(
    "ix_file_transfer_record_recording_occurred_at",
    file_transfer_record.c.recording_id,
    file_transfer_record.c.occurred_at,
)
Index("ix_metadata_draft_recording_version", metadata_draft.c.recording_id, metadata_draft.c.version)
Index(
    "ix_reviewed_metadata_recording_version",
    reviewed_metadata.c.recording_id,
    reviewed_metadata.c.version,
)
Index("ix_action_macro_recording_version", action_macro.c.recording_id, action_macro.c.version)
Index(
    "ix_parameter_definition_owner_action",
    parameter_definition.c.owner_kind,
    parameter_definition.c.action_id,
    parameter_definition.c.action_version,
)
Index(
    "ix_execution_run_action_ref",
    execution_run.c.action_kind,
    execution_run.c.action_id,
    execution_run.c.action_version,
)
