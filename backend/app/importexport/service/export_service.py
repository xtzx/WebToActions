from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from app.action.domain import ActionMacro
from app.action.repository import ActionMacroRepository
from app.execution.domain.execution_run import ExecutionRun
from app.execution.repository import ExecutionRunRepository
from app.importexport.domain import (
    CURRENT_PACKAGE_FORMAT_VERSION,
    ExecutionRunReference,
    ExportBundle,
    ExportScope,
    RecordingBundleManifest,
    VersionedArtifactReference,
)
from app.importexport.service._bundle_codec import (
    RECORDING_AGGREGATE_PATH,
    serialize_recording_aggregate,
)
from app.infrastructure.storage.storage_bootstrap import StorageLayout
from app.recording.repository import RecordingAggregate, RecordingRepository

LOGIN_STATE_EXCLUDED_WARNING = (
    "浏览器 profile 与活跃登录态不会随资料包导出；导入后的会话仅保留历史上下文，"
    "如需继续执行请准备新的可用会话。"
)
MANIFEST_PATH = "manifest.json"


@dataclass(frozen=True)
class ExportBundleResult:
    bundle: ExportBundle
    archive_path: Path
    download_name: str


class ExportService:
    def __init__(
        self,
        *,
        recording_repository: RecordingRepository,
        action_repository: ActionMacroRepository,
        execution_repository: ExecutionRunRepository,
        storage_layout: StorageLayout,
    ) -> None:
        self._recording_repository = recording_repository
        self._action_repository = action_repository
        self._execution_repository = execution_repository
        self._storage_layout = storage_layout

    def export_recording_bundle(self, recording_id: str) -> ExportBundleResult:
        aggregate = self._recording_repository.get(recording_id)
        if aggregate is None:
            raise KeyError(f"Recording {recording_id} not found.")

        latest_actions = tuple(
            item for item in self._action_repository.list() if item.recording_id == recording_id
        )
        action_ids = {item.id for item in latest_actions}
        executions = tuple(
            item for item in self._execution_repository.list() if item.action_id in action_ids
        )
        actions_by_version: dict[tuple[str, int], ActionMacro] = {
            (item.id, item.version): item for item in latest_actions
        }
        for execution in executions:
            action = self._action_repository.get(execution.action_id, execution.action_version)
            if action is None:
                raise ValueError(
                    "Execution run "
                    f"{execution.id} references missing action macro "
                    f"{execution.action_id} v{execution.action_version}."
                )
            if action.recording_id != recording_id:
                raise ValueError(
                    "Execution run "
                    f"{execution.id} references action macro {action.id} "
                    "outside the exported recording."
                )
            actions_by_version[(action.id, action.version)] = action
        actions = tuple(
            sorted(
                actions_by_version.values(),
                key=lambda item: (item.id, item.version),
            )
        )
        action_paths = [_relative_path(self._storage_layout.root, self._action_file_path(item)) for item in actions]
        execution_paths = [
            _relative_path(self._storage_layout.root, self._execution_summary_path(item))
            for item in executions
        ]
        file_manifest = _dedupe(
            [
                MANIFEST_PATH,
                RECORDING_AGGREGATE_PATH,
                *action_paths,
                *execution_paths,
                *[
                    _relative_path(self._storage_layout.root, path)
                    for path in _execution_log_paths(self._storage_layout, executions)
                ],
                *_recording_blob_keys(aggregate),
            ]
        )
        bundle = ExportBundle(
            id=f"bundle-{recording_id}-{uuid4().hex[:8]}",
            version=1,
            export_scope=ExportScope.RECORDING,
            package_format_version=CURRENT_PACKAGE_FORMAT_VERSION,
            recording_ids=[recording_id],
            reviewed_metadata_refs=[
                VersionedArtifactReference(artifact_id=item.id, version=item.version)
                for item in aggregate.reviewed_metadata
            ],
            action_macro_refs=[
                VersionedArtifactReference(artifact_id=item.id, version=item.version)
                for item in actions
            ],
            business_action_refs=[],
            file_manifest=file_manifest,
        )
        manifest = RecordingBundleManifest(
            bundle=bundle,
            recording_aggregate_path=RECORDING_AGGREGATE_PATH,
            action_paths=action_paths,
            execution_paths=execution_paths,
            execution_run_refs=[
                ExecutionRunReference(
                    execution_id=item.id,
                    action_id=item.action_id,
                    action_version=item.action_version,
                    status=item.status.value,
                )
                for item in executions
            ],
            warnings=[LOGIN_STATE_EXCLUDED_WARNING],
        )

        archive_path = self._storage_layout.export_bundle_path(bundle.id, bundle.version)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
            archive.writestr(
                MANIFEST_PATH,
                manifest.model_dump_json(indent=2, ensure_ascii=False),
            )
            archive.writestr(
                RECORDING_AGGREGATE_PATH,
                json.dumps(
                    serialize_recording_aggregate(aggregate),
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            for action in actions:
                path = self._action_file_path(action)
                archive.writestr(
                    _relative_path(self._storage_layout.root, path),
                    _read_or_dump_json(path, action.model_dump(mode="json")),
                )
            for execution in executions:
                summary_path = self._execution_summary_path(execution)
                archive.writestr(
                    _relative_path(self._storage_layout.root, summary_path),
                    _read_or_dump_json(summary_path, execution.model_dump(mode="json")),
                )
                for log_path in _execution_log_paths(self._storage_layout, (execution,)):
                    archive.writestr(
                        _relative_path(self._storage_layout.root, log_path),
                        _read_file_bytes(log_path),
                    )
            for blob_key in _recording_blob_keys(aggregate):
                blob_path = self._storage_layout.root / blob_key
                archive.writestr(blob_key, _read_file_bytes(blob_path))

        return ExportBundleResult(
            bundle=bundle,
            archive_path=archive_path,
            download_name=f"{recording_id}-bundle.zip",
        )

    def _action_file_path(self, action: ActionMacro) -> Path:
        return self._storage_layout.action_macro_version_path(action.id, action.version)

    def _execution_summary_path(self, execution: ExecutionRun) -> Path:
        return self._storage_layout.execution_run_summary_path(execution.id)


def _recording_blob_keys(aggregate: RecordingAggregate) -> list[str]:
    blob_keys: list[str] = []
    for item in aggregate.request_response_records:
        if item.request_body_blob_key:
            blob_keys.append(item.request_body_blob_key)
        if item.response_body_blob_key:
            blob_keys.append(item.response_body_blob_key)
    for item in aggregate.session_state_snapshots:
        capture = item.storage_summary.get("capture", {})
        blob_key = capture.get("blobKey")
        if isinstance(blob_key, str) and blob_key:
            blob_keys.append(blob_key)
    return _dedupe(blob_keys)


def _execution_log_paths(
    storage_layout: StorageLayout,
    executions: tuple[ExecutionRun, ...],
) -> list[Path]:
    paths: list[Path] = []
    for item in executions:
        log_path = storage_layout.execution_run_logs_dir(item.id) / "step-logs.json"
        if log_path.exists():
            paths.append(log_path)
    return paths


def _read_or_dump_json(path: Path, payload: object) -> bytes:
    if path.exists():
        return _read_file_bytes(path)
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def _read_file_bytes(path: Path) -> bytes:
    if not path.exists():
        raise ValueError(f"Required export file {path} does not exist.")
    return path.read_bytes()


def _relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
