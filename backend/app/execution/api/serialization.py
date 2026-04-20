from __future__ import annotations

import json
from typing import Any

from app.core.domain_model import FrozenDict, FrozenList
from app.execution.domain.execution_run import ExecutionRun


def serialize_execution_run(run: ExecutionRun) -> dict[str, object]:
    return {
        "id": run.id,
        "actionKind": run.action_kind.value,
        "actionId": run.action_id,
        "actionVersion": run.action_version,
        "browserSessionId": run.browser_session_id,
        "parametersSnapshot": _to_plain_json(run.parameters_snapshot),
        "status": run.status.value,
        "createdAt": run.created_at.isoformat(),
        "startedAt": run.started_at.isoformat() if run.started_at is not None else None,
        "endedAt": run.ended_at.isoformat() if run.ended_at is not None else None,
        "stepLogs": list(run.step_logs),
        "failureReason": run.failure_reason,
        "diagnostics": _to_plain_json(run.diagnostics),
    }


def encode_sse(payload: dict[str, Any]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _to_plain_json(value):  # type: ignore[no-untyped-def]
    if isinstance(value, FrozenList):
        return [_to_plain_json(item) for item in value]
    if isinstance(value, (list, tuple)):
        return [_to_plain_json(item) for item in value]
    if isinstance(value, FrozenDict):
        return {key: _to_plain_json(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {key: _to_plain_json(item) for key, item in value.items()}
    return value
