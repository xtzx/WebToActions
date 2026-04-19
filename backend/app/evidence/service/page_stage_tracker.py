from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.evidence.domain import PageStage


@dataclass
class _StageDraft:
    id: str
    url: str
    name: str
    started_at: datetime
    ended_at: datetime | None = None
    related_request_ids: list[str] = field(default_factory=list)


class PageStageTracker:
    def __init__(self, *, recording_id: str) -> None:
        self._recording_id = recording_id
        self._stages: list[_StageDraft] = []
        self._counter = 0

    def on_navigation(self, *, url: str, title: str | None) -> None:
        observed_at = datetime.now(UTC)
        if self._stages and self._stages[-1].ended_at is None:
            self._stages[-1].ended_at = observed_at

        self._counter += 1
        self._stages.append(
            _StageDraft(
                id=f"stage-{self._counter}",
                url=url,
                name=title or url,
                started_at=observed_at,
            )
        )

    def link_request(self, request_id: str) -> str | None:
        stage = self.current_stage()
        if stage is None:
            return None
        if request_id not in stage.related_request_ids:
            stage.related_request_ids.append(request_id)
        return stage.id

    def finish(self) -> None:
        if self._stages and self._stages[-1].ended_at is None:
            self._stages[-1].ended_at = datetime.now(UTC)

    def current_stage(self) -> _StageDraft | None:
        if not self._stages:
            return None
        return self._stages[-1]

    def current_url(self) -> str | None:
        stage = self.current_stage()
        return stage.url if stage is not None else None

    def count(self) -> int:
        return len(self._stages)

    def snapshot(self) -> tuple[PageStage, ...]:
        return tuple(
            PageStage(
                id=stage.id,
                recording_id=self._recording_id,
                url=stage.url,
                name=stage.name,
                started_at=stage.started_at,
                ended_at=stage.ended_at,
                related_request_ids=stage.related_request_ids,
            )
            for stage in self._stages
        )
