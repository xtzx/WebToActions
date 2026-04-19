from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.infrastructure.storage import StorageLayout


class EvidenceWriter:
    def __init__(self, *, storage_layout: StorageLayout) -> None:
        self._storage_layout = storage_layout

    def write_request_body(
        self,
        *,
        recording_id: str,
        request_id: str,
        payload: bytes | None,
    ) -> str | None:
        if payload is None:
            return None
        blob_key = self._storage_layout.request_body_blob_key(recording_id, request_id)
        self._write_bytes(blob_key, payload)
        return blob_key

    def write_response_body(
        self,
        *,
        recording_id: str,
        request_id: str,
        payload: bytes | None,
    ) -> str | None:
        if payload is None:
            return None
        blob_key = self._storage_layout.response_body_blob_key(recording_id, request_id)
        self._write_bytes(blob_key, payload)
        return blob_key

    def write_session_state(
        self,
        *,
        recording_id: str,
        snapshot_id: str,
        payload: dict[str, Any],
    ) -> str:
        blob_key = self._storage_layout.session_state_blob_key(recording_id, snapshot_id)
        self._write_text(blob_key, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        return blob_key

    def _write_bytes(self, blob_key: str, payload: bytes) -> None:
        path = self._resolve(blob_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    def _write_text(self, blob_key: str, payload: str) -> None:
        path = self._resolve(blob_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")

    def _resolve(self, blob_key: str) -> Path:
        return self._storage_layout.root / blob_key
