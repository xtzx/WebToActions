from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path, PurePosixPath


def _safe_segment(value: str) -> str:
    segment = value.strip()
    if not segment:
        raise ValueError("Path segment cannot be empty.")

    return segment.replace("/", "_").replace("\\", "_")


def _safe_file_name(file_name: str) -> str:
    name = Path(file_name).name.strip()
    if not name:
        raise ValueError("File name cannot be empty.")

    return name


@dataclass(frozen=True)
class ObjectDigest:
    sha256: str
    size_bytes: int

    @classmethod
    def from_bytes(cls, payload: bytes) -> "ObjectDigest":
        return cls(sha256=sha256(payload).hexdigest(), size_bytes=len(payload))


@dataclass(frozen=True)
class StorageLayout:
    root: Path

    @property
    def database_path(self) -> Path:
        return self.root / "app.db"

    @property
    def evidence_root(self) -> Path:
        return self.root / "evidence"

    @property
    def actions_root(self) -> Path:
        return self.root / "actions"

    @property
    def runs_root(self) -> Path:
        return self.root / "runs"

    @property
    def exports_root(self) -> Path:
        return self.root / "exports"

    def recording_root(self, recording_id: str) -> Path:
        return self.evidence_root / f"rec_{_safe_segment(recording_id)}"

    def stage_index_path(self, recording_id: str) -> Path:
        return self.recording_root(recording_id) / "stage_index.json"

    def request_body_blob_key(self, recording_id: str, request_id: str) -> str:
        return str(
            PurePosixPath("evidence")
            / f"rec_{_safe_segment(recording_id)}"
            / "requests"
            / _safe_segment(request_id)
            / "request-body.bin"
        )

    def response_body_blob_key(self, recording_id: str, request_id: str) -> str:
        return str(
            PurePosixPath("evidence")
            / f"rec_{_safe_segment(recording_id)}"
            / "responses"
            / _safe_segment(request_id)
            / "response-body.bin"
        )

    def session_state_blob_key(self, recording_id: str, snapshot_id: str) -> str:
        return str(
            PurePosixPath("evidence")
            / f"rec_{_safe_segment(recording_id)}"
            / "session_state"
            / f"{_safe_segment(snapshot_id)}.json"
        )

    def file_transfer_blob_key(
        self,
        recording_id: str,
        transfer_id: str,
        file_name: str,
    ) -> str:
        return str(
            PurePosixPath("evidence")
            / f"rec_{_safe_segment(recording_id)}"
            / "file_transfers"
            / _safe_segment(transfer_id)
            / _safe_file_name(file_name)
        )

    def action_macro_version_path(self, action_id: str, version: int) -> Path:
        return self.actions_root / f"macro_{_safe_segment(action_id)}" / f"version_{version}.json"

    def business_action_version_path(self, action_id: str, version: int) -> Path:
        return self.actions_root / f"business_{_safe_segment(action_id)}" / f"version_{version}.json"

    def execution_run_summary_path(self, execution_id: str) -> Path:
        return self.runs_root / f"run_{_safe_segment(execution_id)}" / "run.json"

    def execution_run_logs_dir(self, execution_id: str) -> Path:
        return self.runs_root / f"run_{_safe_segment(execution_id)}" / "logs"

    def export_bundle_path(self, bundle_id: str, version: int) -> Path:
        return self.exports_root / f"bundle_{_safe_segment(bundle_id)}" / f"version_{version}.zip"


def bootstrap_storage_layout(root: Path) -> StorageLayout:
    layout = StorageLayout(root=root)
    layout.root.mkdir(parents=True, exist_ok=True)
    layout.evidence_root.mkdir(parents=True, exist_ok=True)
    layout.actions_root.mkdir(parents=True, exist_ok=True)
    layout.runs_root.mkdir(parents=True, exist_ok=True)
    layout.exports_root.mkdir(parents=True, exist_ok=True)
    return layout
