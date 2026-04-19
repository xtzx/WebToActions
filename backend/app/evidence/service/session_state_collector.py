from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.evidence.domain import SessionStateSnapshot
from app.evidence.service.evidence_writer import EvidenceWriter


class SessionStateCollector:
    def build_snapshot(
        self,
        *,
        recording_id: str,
        browser_session_id: str,
        page_stage_id: str | None,
        snapshot_id: str,
        browser_snapshot: dict[str, Any],
        evidence_writer: EvidenceWriter,
    ) -> SessionStateSnapshot:
        cookie_summary = _string_dict(browser_snapshot.get("cookieSummary"))
        storage_summary = _nested_string_dict(browser_snapshot.get("storageSummary"))
        blob_key = evidence_writer.write_session_state(
            recording_id=recording_id,
            snapshot_id=snapshot_id,
            payload={
                "cookieSummary": cookie_summary,
                "storageSummary": storage_summary,
                "currentUrl": browser_snapshot.get("currentUrl"),
                "pageTitle": browser_snapshot.get("pageTitle"),
                "loginSiteSummaries": browser_snapshot.get("loginSiteSummaries", []),
            },
        )
        storage_summary = dict(storage_summary)
        capture = dict(storage_summary.get("capture", {}))
        capture["blobKey"] = blob_key
        storage_summary["capture"] = capture
        return SessionStateSnapshot(
            id=snapshot_id,
            recording_id=recording_id,
            browser_session_id=browser_session_id,
            page_stage_id=page_stage_id,
            captured_at=datetime.now(UTC),
            cookie_summary=cookie_summary,
            storage_summary=storage_summary,
        )


def _string_dict(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        return {}
    return {str(key): str(item) for key, item in value.items()}


def _nested_string_dict(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for key, item in value.items():
        if not isinstance(item, dict):
            continue
        result[str(key)] = {str(inner_key): str(inner_value) for inner_key, inner_value in item.items()}
    return result
