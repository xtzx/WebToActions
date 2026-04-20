from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from pydantic import ValidationError
from sqlalchemy.orm import Session, sessionmaker

from app.action.domain import ActionMacro
from app.action.repository import ActionMacroRepository
from app.execution.domain.execution_run import ExecutionRun
from app.execution.repository import ExecutionRunRepository
from app.importexport.domain import (
    CURRENT_PACKAGE_FORMAT_VERSION,
    RecordingBundleManifest,
)
from app.importexport.service._bundle_codec import (
    RECORDING_AGGREGATE_PATH,
    deserialize_action_macro,
    deserialize_execution_run,
    deserialize_recording_aggregate,
    ensure_safe_archive_path,
)
from app.recording.repository import RecordingAggregate, RecordingRepository
from app.session.domain.browser_session import BrowserSessionStatus
from app.session.service.browser_session_manager import BrowserSessionManager

MANIFEST_PATH = "manifest.json"


class ImportConflictError(ValueError):
    pass


@dataclass(frozen=True)
class ImportBundleResult:
    recording_id: str
    action_ids: list[str]
    execution_ids: list[str]
    warnings: list[str]


class ImportService:
    def __init__(
        self,
        *,
        recording_repository: RecordingRepository,
        action_repository: ActionMacroRepository,
        execution_repository: ExecutionRunRepository,
        session_manager: BrowserSessionManager,
        session_factory: sessionmaker[Session],
        storage_root: Path,
    ) -> None:
        self._recording_repository = recording_repository
        self._action_repository = action_repository
        self._execution_repository = execution_repository
        self._session_manager = session_manager
        self._session_factory = session_factory
        self._storage_root = storage_root

    def import_recording_bundle(self, payload: bytes) -> ImportBundleResult:
        try:
            archive = ZipFile(BytesIO(payload))
        except BadZipFile as exc:
            raise ValueError("Uploaded bundle is not a valid zip archive.") from exc

        with archive:
            manifest = self._load_manifest(archive)
            aggregate = self._load_recording_aggregate(
                archive,
                manifest.recording_aggregate_path,
            )
            aggregate = self._sanitize_imported_aggregate(aggregate)
            actions = self._load_actions(archive, manifest.action_paths)
            executions = self._load_executions(archive, manifest.execution_paths)
            self._validate_bundle_references(
                recording_id=aggregate.recording.id,
                manifest=manifest,
                actions=actions,
                executions=executions,
            )
            self._validate_recording_blob_references(
                aggregate,
                manifest.bundle.file_manifest,
            )
            self._validate_file_manifest(archive, manifest.bundle.file_manifest)
            self._assert_no_conflicts(
                aggregate.recording.id,
                aggregate.browser_session.id if aggregate.browser_session else None,
                actions,
                executions,
            )
            cleanup_profile_dir = self._profile_dir_for_cleanup(aggregate)
            cleanup_file_manifest = [
                ensure_safe_archive_path(entry).as_posix()
                for entry in manifest.bundle.file_manifest
                if entry not in {MANIFEST_PATH, RECORDING_AGGREGATE_PATH}
            ]
            try:
                with self._session_factory.begin() as session:
                    self._extract_files(archive, manifest.bundle.file_manifest)
                    self._recording_repository.save(aggregate, session=session)
                    if aggregate.browser_session is not None:
                        self._session_manager.profile_dir(aggregate.browser_session.profile_id)

                    action_ids: list[str] = []
                    for action in actions:
                        self._action_repository.save(action, session=session)
                        if action.id not in action_ids:
                            action_ids.append(action.id)

                    execution_ids: list[str] = []
                    for execution in executions:
                        self._execution_repository.save(execution, session=session)
                        execution_ids.append(execution.id)
            except Exception:
                self._cleanup_import_artifacts(
                    cleanup_file_manifest,
                    cleanup_profile_dir,
                )
                raise

        return ImportBundleResult(
            recording_id=aggregate.recording.id,
            action_ids=action_ids,
            execution_ids=execution_ids,
            warnings=list(manifest.warnings),
        )

    def _profile_dir_for_cleanup(self, aggregate: RecordingAggregate) -> Path | None:
        browser_session = aggregate.browser_session
        if browser_session is None:
            return None
        profile_dir = self._storage_root / "profiles" / browser_session.profile_id
        if profile_dir.exists():
            return None
        return profile_dir

    def _sanitize_imported_aggregate(self, aggregate):
        browser_session = aggregate.browser_session
        if browser_session is None:
            return aggregate
        sanitized_session = browser_session.validated_copy(
            status=BrowserSessionStatus.RELOGIN_REQUIRED,
            login_site_summaries=[],
        )
        return aggregate.__class__(
            recording=aggregate.recording,
            browser_session=sanitized_session,
            page_stages=aggregate.page_stages,
            request_response_records=aggregate.request_response_records,
            session_state_snapshots=aggregate.session_state_snapshots,
            file_transfer_records=aggregate.file_transfer_records,
            metadata_drafts=aggregate.metadata_drafts,
            reviewed_metadata=aggregate.reviewed_metadata,
        )

    def _load_manifest(self, archive: ZipFile) -> RecordingBundleManifest:
        if MANIFEST_PATH not in archive.namelist():
            raise ValueError("Bundle manifest is missing.")
        try:
            manifest = RecordingBundleManifest.model_validate_json(archive.read(MANIFEST_PATH))
        except ValidationError as exc:
            raise ValueError("Bundle manifest is invalid.") from exc
        if manifest.bundle.package_format_version != CURRENT_PACKAGE_FORMAT_VERSION:
            raise ValueError("Unsupported bundle package format version.")
        if manifest.bundle.export_scope.value != "recording":
            raise ValueError("Only recording bundles can be imported in stage 6.")
        return manifest

    def _load_recording_aggregate(self, archive: ZipFile, path: str):
        try:
            return deserialize_recording_aggregate(
                self._read_json_entry(
                    archive,
                    path,
                    "recording aggregate payload",
                )
            )
        except ValidationError as exc:
            raise ValueError("Bundle recording aggregate payload is invalid.") from exc

    def _load_actions(self, archive: ZipFile, paths: list[str]) -> list[ActionMacro]:
        actions: list[ActionMacro] = []
        for path in paths:
            try:
                actions.append(
                    deserialize_action_macro(
                        self._read_json_entry(
                            archive,
                            path,
                            "action payload",
                        )
                    )
                )
            except ValidationError as exc:
                raise ValueError(f"Bundle action payload {path} is invalid.") from exc
        return actions

    def _load_executions(self, archive: ZipFile, paths: list[str]) -> list[ExecutionRun]:
        executions: list[ExecutionRun] = []
        for path in paths:
            try:
                executions.append(
                    deserialize_execution_run(
                        self._read_json_entry(
                            archive,
                            path,
                            "execution payload",
                        )
                    )
                )
            except ValidationError as exc:
                raise ValueError(f"Bundle execution payload {path} is invalid.") from exc
        return executions

    def _validate_bundle_references(
        self,
        *,
        recording_id: str,
        manifest: RecordingBundleManifest,
        actions: list[ActionMacro],
        executions: list[ExecutionRun],
    ) -> None:
        for action in actions:
            if action.recording_id != recording_id:
                raise ValueError(
                    f"Action macro {action.id} does not belong to recording {recording_id}."
                )

        available_action_versions = {(action.id, action.version) for action in actions}
        execution_refs_by_id = {
            item.execution_id: item for item in manifest.execution_run_refs
        }
        execution_ids = {execution.id for execution in executions}

        if set(execution_refs_by_id) != execution_ids:
            raise ValueError("Bundle execution references do not match execution payloads.")

        for execution in executions:
            reference = execution_refs_by_id[execution.id]
            if (
                reference.action_id != execution.action_id
                or reference.action_version != execution.action_version
                or reference.status != execution.status.value
            ):
                raise ValueError(
                    f"Bundle execution reference for {execution.id} does not match execution payload."
                )
            if (execution.action_id, execution.action_version) not in available_action_versions:
                raise ValueError(
                    "Execution run "
                    f"{execution.id} references missing action macro "
                    f"{execution.action_id} v{execution.action_version}."
                )

    def _validate_recording_blob_references(
        self,
        aggregate: RecordingAggregate,
        file_manifest: list[str],
    ) -> None:
        manifest_entries = set(file_manifest)
        missing_entries = [
            entry for entry in _recording_blob_keys(aggregate) if entry not in manifest_entries
        ]
        if missing_entries:
            raise ValueError(
                "Bundle manifest is missing recording evidence files: "
                + ", ".join(missing_entries)
            )

    def _read_json_entry(self, archive: ZipFile, path: str, label: str) -> dict[str, object]:
        safe_path = ensure_safe_archive_path(path).as_posix()
        if safe_path not in archive.namelist():
            raise ValueError(f"Bundle is missing required {label} file {safe_path}.")
        try:
            return json.loads(archive.read(safe_path))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Bundle contains invalid JSON in {label} file {safe_path}.") from exc

    def _assert_no_conflicts(
        self,
        recording_id: str,
        session_id: str | None,
        actions: list[ActionMacro],
        executions: list[ExecutionRun],
    ) -> None:
        if self._recording_repository.get(recording_id) is not None:
            raise ImportConflictError(f"Recording {recording_id} already exists.")
        if session_id is not None and self._session_manager.get_session(session_id) is not None:
            raise ImportConflictError(f"Browser session {session_id} already exists.")

        for action in actions:
            if self._action_repository.get(action.id) is not None:
                raise ImportConflictError(f"Action macro {action.id} already exists.")

        for execution in executions:
            if self._execution_repository.get(execution.id) is not None:
                raise ImportConflictError(f"Execution run {execution.id} already exists.")

    def _validate_file_manifest(self, archive: ZipFile, file_manifest: list[str]) -> None:
        for entry in file_manifest:
            safe_path = ensure_safe_archive_path(entry).as_posix()
            if safe_path not in archive.namelist():
                raise ValueError(f"Bundle is missing required file {safe_path}.")

    def _extract_files(self, archive: ZipFile, file_manifest: list[str]) -> None:
        for entry in file_manifest:
            safe_path = ensure_safe_archive_path(entry)
            normalized_entry = safe_path.as_posix()
            if normalized_entry in {MANIFEST_PATH, RECORDING_AGGREGATE_PATH}:
                continue
            destination = self._storage_root / safe_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(archive.read(normalized_entry))

    def _cleanup_import_artifacts(
        self,
        file_manifest: list[str],
        profile_dir: Path | None,
    ) -> None:
        for entry in file_manifest:
            destination = self._storage_root / ensure_safe_archive_path(entry)
            if destination.exists():
                destination.unlink()
            self._cleanup_empty_parents(destination.parent)

        if profile_dir is not None and profile_dir.exists():
            profile_dir.rmdir()
            self._cleanup_empty_parents(profile_dir.parent)

    def _cleanup_empty_parents(self, path: Path) -> None:
        current = path
        while current != self._storage_root and current.exists():
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent


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
    return blob_keys
