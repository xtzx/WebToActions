from pathlib import Path

from app.infrastructure.storage.storage_bootstrap import (
    ObjectDigest,
    StorageLayout,
    bootstrap_storage_layout,
)


def test_bootstrap_storage_layout_creates_expected_stage2_directories(
    tmp_path: Path,
) -> None:
    layout = bootstrap_storage_layout(tmp_path / ".webtoactions")

    assert layout.root.is_dir()
    assert layout.evidence_root.is_dir()
    assert layout.actions_root.is_dir()
    assert layout.runs_root.is_dir()
    assert layout.exports_root.is_dir()
    assert layout.database_path == layout.root / "app.db"
    assert layout.recording_root("recording-1") == layout.root / "evidence" / "rec_recording-1"


def test_storage_layout_builds_stable_blob_keys_and_digests(tmp_path: Path) -> None:
    layout = StorageLayout(root=tmp_path / ".webtoactions")

    assert layout.request_body_blob_key("recording-1", "request-1") == (
        "evidence/rec_recording-1/requests/request-1/request-body.bin"
    )
    assert layout.response_body_blob_key("recording-1", "request-1") == (
        "evidence/rec_recording-1/responses/request-1/response-body.bin"
    )
    assert layout.session_state_blob_key("recording-1", "snapshot-1") == (
        "evidence/rec_recording-1/session_state/snapshot-1.json"
    )
    assert layout.file_transfer_blob_key("recording-1", "transfer-1", "invoice.pdf") == (
        "evidence/rec_recording-1/file_transfers/transfer-1/invoice.pdf"
    )
    assert layout.action_macro_version_path("macro-1", 2) == (
        tmp_path / ".webtoactions" / "actions" / "macro_macro-1" / "version_2.json"
    )
    assert layout.business_action_version_path("business-1", 3) == (
        tmp_path / ".webtoactions" / "actions" / "business_business-1" / "version_3.json"
    )
    assert layout.execution_run_summary_path("run-1") == (
        tmp_path / ".webtoactions" / "runs" / "run_run-1" / "run.json"
    )
    assert layout.export_bundle_path("bundle-1", 4) == (
        tmp_path / ".webtoactions" / "exports" / "bundle_bundle-1" / "version_4.zip"
    )

    digest = ObjectDigest.from_bytes(b"hello world")
    assert digest.size_bytes == 11
    assert (
        digest.sha256
        == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    )
