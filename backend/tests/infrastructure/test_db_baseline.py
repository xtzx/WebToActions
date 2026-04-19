from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.infrastructure.db.schema import metadata


def test_versioned_tables_use_stable_id_plus_version_primary_keys() -> None:
    assert list(metadata.tables["metadata_draft"].primary_key.columns.keys()) == [
        "id",
        "version",
    ]
    assert list(metadata.tables["reviewed_metadata"].primary_key.columns.keys()) == [
        "id",
        "version",
    ]
    assert list(metadata.tables["action_macro"].primary_key.columns.keys()) == [
        "id",
        "version",
    ]
    assert list(metadata.tables["business_action"].primary_key.columns.keys()) == [
        "id",
        "version",
    ]
    assert list(metadata.tables["export_bundle"].primary_key.columns.keys()) == [
        "id",
        "version",
    ]


def test_alembic_upgrade_creates_stage2_index_tables(tmp_path: Path) -> None:
    database_path = tmp_path / ".webtoactions" / "app.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    alembic_config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_config.set_main_option(
        "script_location",
        str(Path(__file__).resolve().parents[2] / "alembic"),
    )
    alembic_config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")

    command.upgrade(alembic_config, "head")

    inspector = inspect(create_engine(f"sqlite:///{database_path}"))

    assert {
        "browser_session",
        "recording",
        "page_stage",
        "request_response_record",
        "session_state_snapshot",
        "file_transfer_record",
        "metadata_draft",
        "reviewed_metadata",
        "action_macro",
        "business_action",
        "parameter_definition",
        "execution_run",
        "export_bundle",
    }.issubset(set(inspector.get_table_names()))

    request_columns = {
        column["name"] for column in inspector.get_columns("request_response_record")
    }
    assert {"request_body_blob_key", "response_body_blob_key", "page_stage_id"}.issubset(
        request_columns
    )

    parameter_columns = {
        column["name"] for column in inspector.get_columns("parameter_definition")
    }
    assert {"owner_kind", "action_id", "action_version", "parameter_kind"}.issubset(
        parameter_columns
    )

    bundle_columns = {column["name"] for column in inspector.get_columns("export_bundle")}
    assert {"version", "previous_version", "bundle_blob_key"}.issubset(bundle_columns)
