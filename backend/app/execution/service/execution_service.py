from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from queue import Empty, Queue
from threading import Lock, Thread
from typing import Any
from uuid import uuid4

from app.action.domain import ActionKind, ActionMacro, ParameterDefinition, ParameterKind
from app.action.repository import ActionMacroRepository
from app.execution.domain.execution_run import ExecutionRun
from app.execution.repository import ExecutionRunRepository
from app.execution.service.browser_replayer import (
    BrowserReplayer,
    ReplayCallbacks,
    ReplayRequestStep,
)
from app.recording.domain.recording import RecordingStatus
from app.recording.repository import RecordingAggregate, RecordingRepository
from app.session.domain.browser_session import BrowserSessionStatus
from app.session.service.browser_session_manager import BrowserSessionManager


@dataclass(frozen=True)
class ExecutionSnapshot:
    execution_id: str
    status: str
    current_step_id: str | None
    current_step_title: str | None
    current_url: str | None
    log_count: int
    failure_reason: str | None
    updated_at: str


@dataclass
class _ExecutionState:
    run: ExecutionRun
    current_step_id: str | None = None
    current_step_title: str | None = None
    current_url: str | None = None


class ExecutionService:
    def __init__(
        self,
        *,
        action_repository: ActionMacroRepository,
        recording_repository: RecordingRepository,
        execution_repository: ExecutionRunRepository,
        session_manager: BrowserSessionManager,
        browser_replayer: BrowserReplayer,
        storage_root: Path,
    ) -> None:
        self._action_repository = action_repository
        self._recording_repository = recording_repository
        self._execution_repository = execution_repository
        self._session_manager = session_manager
        self._browser_replayer = browser_replayer
        self._storage_root = storage_root
        self._lock = Lock()
        self._active_runs: dict[str, _ExecutionState] = {}
        self._snapshots: dict[str, ExecutionSnapshot] = {}
        self._subscribers: dict[str, list[Queue[ExecutionSnapshot]]] = {}

    def list_runs(self) -> tuple[ExecutionRun, ...]:
        persisted = {item.id: item for item in self._execution_repository.list()}
        with self._lock:
            for execution_id, state in self._active_runs.items():
                persisted[execution_id] = state.run
        return tuple(
            sorted(
                persisted.values(),
                key=lambda item: item.created_at,
                reverse=True,
            )
        )

    def get_run(self, execution_id: str) -> ExecutionRun | None:
        with self._lock:
            active = self._active_runs.get(execution_id)
        if active is not None:
            return active.run
        return self._execution_repository.get(execution_id)

    def get_snapshot(self, execution_id: str) -> ExecutionSnapshot | None:
        with self._lock:
            snapshot = self._snapshots.get(execution_id)
        if snapshot is not None:
            return snapshot
        run = self.get_run(execution_id)
        if run is None:
            return None
        return ExecutionSnapshot(
            execution_id=run.id,
            status=run.status.value,
            current_step_id=run.diagnostics.get("failedStepId"),
            current_step_title=run.diagnostics.get("failedStepTitle"),
            current_url=run.diagnostics.get("finalUrl"),
            log_count=len(run.step_logs),
            failure_reason=run.failure_reason,
            updated_at=_utc_now(),
        )

    def subscribe(
        self,
        execution_id: str,
    ) -> tuple[ExecutionSnapshot | None, Queue[ExecutionSnapshot]]:
        queue: Queue[ExecutionSnapshot] = Queue()
        with self._lock:
            self._subscribers.setdefault(execution_id, []).append(queue)
            latest = self._snapshots.get(execution_id)
        if latest is None:
            latest = self.get_snapshot(execution_id)
        return latest, queue

    def unsubscribe(
        self,
        execution_id: str,
        queue: Queue[ExecutionSnapshot],
    ) -> None:
        with self._lock:
            subscribers = self._subscribers.get(execution_id)
            if subscribers is None:
                return
            self._subscribers[execution_id] = [item for item in subscribers if item is not queue]
            if not self._subscribers[execution_id]:
                self._subscribers.pop(execution_id, None)

    def wait_for_event(
        self,
        queue: Queue[ExecutionSnapshot],
        *,
        timeout_seconds: float,
    ) -> ExecutionSnapshot | None:
        try:
            return queue.get(timeout=timeout_seconds)
        except Empty:
            return None

    def start_execution(
        self,
        *,
        action_id: str,
        browser_session_id: str,
        parameters: dict[str, Any],
    ) -> ExecutionRun:
        action = self._action_repository.get(action_id)
        if action is None:
            raise KeyError(f"Action macro {action_id} not found.")

        aggregate = self._recording_repository.get(action.recording_id)
        if aggregate is None:
            raise KeyError(f"Recording {action.recording_id} not found.")
        if aggregate.recording.status not in {
            RecordingStatus.PENDING_REVIEW,
            RecordingStatus.MACRO_GENERATED,
        }:
            raise ValueError("Executions are only available after recording review has completed.")

        browser_session = self._session_manager.ensure_session(browser_session_id)
        if browser_session.status != BrowserSessionStatus.AVAILABLE:
            raise ValueError("Browser session must be available before starting execution.")

        resolved_parameters = _resolve_parameters(action=action, raw_parameters=parameters)
        execution_id = f"run-{uuid4().hex[:8]}"
        run = ExecutionRun(
            id=execution_id,
            action_kind=ActionKind.ACTION_MACRO,
            action_id=action.id,
            action_version=action.version,
            browser_session_id=browser_session.id,
            parameters_snapshot=resolved_parameters,
        )
        self._execution_repository.save(run)
        with self._lock:
            self._active_runs[execution_id] = _ExecutionState(run=run)
        self._publish(
            ExecutionSnapshot(
                execution_id=execution_id,
                status=run.status.value,
                current_step_id=None,
                current_step_title=None,
                current_url=None,
                log_count=0,
                failure_reason=None,
                updated_at=_utc_now(),
            )
        )

        thread = Thread(
            target=self._run_execution,
            kwargs={
                "execution_id": execution_id,
                "action": action,
                "aggregate": aggregate,
                "browser_session_id": browser_session.id,
                "parameters": resolved_parameters,
            },
            daemon=True,
        )
        thread.start()
        return run

    def _run_execution(
        self,
        *,
        execution_id: str,
        action: ActionMacro,
        aggregate: RecordingAggregate,
        browser_session_id: str,
        parameters: dict[str, Any],
    ) -> None:
        browser_session = self._session_manager.ensure_session(browser_session_id)
        self._set_running(execution_id)
        callbacks = _ExecutionCallbacks(service=self, execution_id=execution_id)

        try:
            resolved_steps = self._resolve_steps(
                action=action,
                aggregate=aggregate,
                parameters=parameters,
            )
            diagnostics = self._browser_replayer.replay(
                profile_dir=self._session_manager.profile_dir(browser_session.profile_id),
                steps=resolved_steps,
                callbacks=callbacks,
            )
            self._finish_success(execution_id=execution_id, diagnostics=diagnostics)
        except Exception as exc:
            self._finish_failure(execution_id=execution_id, reason=str(exc))
        finally:
            latest_state = self.get_run(execution_id)
            if latest_state is not None:
                self._session_manager.update_session_activity(
                    browser_session,
                    login_site_summaries=browser_session.login_site_summaries or action.session_requirements,
                )
            with self._lock:
                self._active_runs.pop(execution_id, None)

    def _resolve_steps(
        self,
        *,
        action: ActionMacro,
        aggregate: RecordingAggregate,
        parameters: dict[str, Any],
    ) -> tuple[ReplayRequestStep, ...]:
        request_by_id = {item.id: item for item in aggregate.request_response_records}
        return tuple(
            ReplayRequestStep(
                id=step.id,
                title=step.title,
                request_id=step.request_id,
                request_method=step.request_method,
                request_url=step.request_url,
                request_headers=_sanitize_headers(
                    tuple((header.name, header.value) for header in request_by_id[step.request_id].request_headers)
                ),
                request_body_text=_resolve_request_body(
                    request_body_text=_load_blob_text(
                        storage_root=self._storage_root,
                        blob_key=request_by_id[step.request_id].request_body_blob_key,
                    ),
                    parameter_definitions=tuple(action.parameter_definitions),
                    parameters=parameters,
                ),
                navigate_url=step.navigate_url,
            )
            for step in action.steps
        )

    def _set_running(self, execution_id: str) -> None:
        with self._lock:
            state = self._active_runs[execution_id]
            state.run = state.run.start()
            run = state.run
        self._execution_repository.save(run)
        self._publish(
            ExecutionSnapshot(
                execution_id=execution_id,
                status=run.status.value,
                current_step_id=None,
                current_step_title=None,
                current_url=None,
                log_count=len(run.step_logs),
                failure_reason=None,
                updated_at=_utc_now(),
            )
        )

    def _append_log(
        self,
        *,
        execution_id: str,
        message: str,
        step_id: str | None,
        step_title: str | None,
        current_url: str | None,
    ) -> None:
        with self._lock:
            state = self._active_runs[execution_id]
            next_logs = [*state.run.step_logs, message]
            diagnostics = dict(state.run.diagnostics)
            if step_id is not None:
                diagnostics["currentStepId"] = step_id
            if step_title is not None:
                diagnostics["currentStepTitle"] = step_title
            if current_url is not None:
                diagnostics["currentUrl"] = current_url
            state.current_step_id = step_id
            state.current_step_title = step_title
            state.current_url = current_url
            state.run = state.run.validated_copy(
                step_logs=next_logs,
                diagnostics=diagnostics,
            )
            run = state.run
        self._publish(
            ExecutionSnapshot(
                execution_id=execution_id,
                status=run.status.value,
                current_step_id=step_id,
                current_step_title=step_title,
                current_url=current_url,
                log_count=len(run.step_logs),
                failure_reason=None,
                updated_at=_utc_now(),
            )
        )

    def _finish_success(self, *, execution_id: str, diagnostics: dict[str, object]) -> None:
        with self._lock:
            state = self._active_runs[execution_id]
            final_base = state.run.validated_copy(diagnostics=diagnostics)
            state.run = final_base.succeed()
            run = state.run
        self._execution_repository.save(run)
        self._publish(
            ExecutionSnapshot(
                execution_id=execution_id,
                status=run.status.value,
                current_step_id=state.current_step_id,
                current_step_title=state.current_step_title,
                current_url=diagnostics.get("finalUrl") if isinstance(diagnostics, dict) else None,
                log_count=len(run.step_logs),
                failure_reason=None,
                updated_at=_utc_now(),
            )
        )

    def _finish_failure(self, *, execution_id: str, reason: str) -> None:
        with self._lock:
            state = self._active_runs[execution_id]
            diagnostics = dict(state.run.diagnostics)
            if state.current_step_id is not None:
                diagnostics["failedStepId"] = state.current_step_id
            if state.current_step_title is not None:
                diagnostics["failedStepTitle"] = state.current_step_title
            state.run = state.run.validated_copy(diagnostics=diagnostics).fail(reason)
            run = state.run
        self._execution_repository.save(run)
        self._publish(
            ExecutionSnapshot(
                execution_id=execution_id,
                status=run.status.value,
                current_step_id=state.current_step_id,
                current_step_title=state.current_step_title,
                current_url=state.current_url,
                log_count=len(run.step_logs),
                failure_reason=run.failure_reason,
                updated_at=_utc_now(),
            )
        )

    def _publish(self, snapshot: ExecutionSnapshot) -> None:
        with self._lock:
            self._snapshots[snapshot.execution_id] = snapshot
            subscribers = list(self._subscribers.get(snapshot.execution_id, []))
        for queue in subscribers:
            queue.put(snapshot)


@dataclass
class _ExecutionCallbacks(ReplayCallbacks):
    service: ExecutionService
    execution_id: str

    def on_log(
        self,
        *,
        message: str,
        step_id: str | None = None,
        step_title: str | None = None,
        current_url: str | None = None,
    ) -> None:
        self.service._append_log(
            execution_id=self.execution_id,
            message=message,
            step_id=step_id,
            step_title=step_title,
            current_url=current_url,
        )


def serialize_execution_snapshot(snapshot: ExecutionSnapshot) -> dict[str, Any]:
    return {
        "executionId": snapshot.execution_id,
        "status": snapshot.status,
        "currentStepId": snapshot.current_step_id,
        "currentStepTitle": snapshot.current_step_title,
        "currentUrl": snapshot.current_url,
        "logCount": snapshot.log_count,
        "failureReason": snapshot.failure_reason,
        "updatedAt": snapshot.updated_at,
    }


def _resolve_parameters(
    *,
    action: ActionMacro,
    raw_parameters: dict[str, Any],
) -> dict[str, Any]:
    definition_names = {item.name for item in action.parameter_definitions}
    unknown_parameters = sorted(set(raw_parameters) - definition_names)
    if unknown_parameters:
        raise ValueError(f"Unknown parameters: {', '.join(unknown_parameters)}")

    resolved: dict[str, Any] = {}
    for definition in action.parameter_definitions:
        value = raw_parameters.get(definition.name, definition.default_value)
        if value is None and definition.required:
            raise ValueError(f"Parameter {definition.name} is required.")
        if value is None:
            continue
        resolved[definition.name] = _coerce_parameter_value(definition, value)
    return resolved


def _coerce_parameter_value(definition: ParameterDefinition, value: Any) -> Any:
    if definition.parameter_kind == ParameterKind.INTEGER:
        return int(value)
    if definition.parameter_kind == ParameterKind.BOOLEAN:
        if isinstance(value, bool):
            return value
        if str(value).lower() in {"true", "1", "yes"}:
            return True
        if str(value).lower() in {"false", "0", "no"}:
            return False
        raise ValueError(f"Parameter {definition.name} must be a boolean.")
    if definition.parameter_kind == ParameterKind.JSON:
        if isinstance(value, (dict, list)):
            return value
        return json.loads(str(value))
    return value


def _sanitize_headers(headers: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    blocked = {
        "content-length",
        "cookie",
        "host",
        "origin",
        "referer",
        "sec-fetch-mode",
        "sec-fetch-site",
        "sec-fetch-dest",
    }
    return tuple((name, value) for name, value in headers if name.lower() not in blocked)


def _load_blob_text(*, storage_root: Path, blob_key: str | None) -> str | None:
    if blob_key is None:
        return None
    path = storage_root / blob_key
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _resolve_request_body(
    *,
    request_body_text: str | None,
    parameter_definitions: tuple[ParameterDefinition, ...],
    parameters: dict[str, Any],
) -> str | None:
    has_request_body_injection = any(
        definition.injection_target.startswith("request.body.")
        and definition.name in parameters
        for definition in parameter_definitions
    )
    body_payload: Any
    if request_body_text is None:
        if not has_request_body_injection:
            return None
        body_payload = {}
    else:
        try:
            body_payload = json.loads(request_body_text)
        except json.JSONDecodeError:
            return request_body_text

    if not isinstance(body_payload, dict):
        return request_body_text

    for definition in parameter_definitions:
        if definition.name not in parameters:
            continue
        if not definition.injection_target.startswith("request.body."):
            continue
        path = definition.injection_target.removeprefix("request.body.")
        _set_nested_value(body_payload, path.split("."), parameters[definition.name])

    return json.dumps(body_payload, ensure_ascii=False)


def _set_nested_value(payload: dict[str, Any], path: list[str], value: Any) -> None:
    current = payload
    for segment in path[:-1]:
        child = current.get(segment)
        if not isinstance(child, dict):
            child = {}
            current[segment] = child
        current = child
    current[path[-1]] = value


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()
