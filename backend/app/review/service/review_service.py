from __future__ import annotations

from dataclasses import replace

from app.recording.repository import RecordingAggregate, RecordingRepository
from app.review.domain import MetadataDraft, ReviewedMetadata


class ReviewService:
    def __init__(self, *, recording_repository: RecordingRepository) -> None:
        self._recording_repository = recording_repository

    def get_review_aggregate(self, recording_id: str) -> RecordingAggregate | None:
        return self._recording_repository.get(recording_id)

    def save_reviewed_metadata(
        self,
        *,
        recording_id: str,
        reviewer: str,
        source_draft_id: str,
        source_draft_version: int,
        key_request_ids: list[str],
        noise_request_ids: list[str],
        field_descriptions: dict[str, str],
        parameter_source_map: dict[str, str],
        action_stage_ids: list[str],
        risk_flags: list[str],
    ) -> ReviewedMetadata:
        aggregate = self._recording_repository.get(recording_id)
        if aggregate is None:
            raise KeyError(f"Recording {recording_id} not found.")

        reviewer = reviewer.strip()
        if not reviewer:
            raise ValueError("Reviewer cannot be blank.")

        draft = self._find_draft(
            aggregate,
            source_draft_id=source_draft_id,
            source_draft_version=source_draft_version,
        )
        if draft is None:
            raise ValueError("Source draft does not exist.")
        latest_draft = self.latest_draft(aggregate)
        if latest_draft is None or latest_draft.version != draft.version:
            raise ValueError("Only the latest draft can be reviewed.")

        request_ids = {item.id for item in aggregate.request_response_records}
        unknown_request_ids = (
            set(key_request_ids).union(noise_request_ids) - request_ids
        )
        if unknown_request_ids:
            raise ValueError("Review payload contains unknown request ids.")

        overlapping_request_ids = set(key_request_ids).intersection(noise_request_ids)
        if overlapping_request_ids:
            raise ValueError("key and noise request ids cannot overlap.")

        stage_ids = {item.id for item in aggregate.page_stages}
        unknown_stage_ids = set(action_stage_ids) - stage_ids
        if unknown_stage_ids:
            raise ValueError("Review payload contains unknown action stage ids.")

        latest_chain_item = self._latest_review_for_draft(
            aggregate,
            source_draft_id=source_draft_id,
        )
        if latest_chain_item is None:
            reviewed = ReviewedMetadata(
                id=f"review-{recording_id}",
                version=1,
                recording_id=recording_id,
                reviewer=reviewer,
                source_draft_id=source_draft_id,
                source_draft_version=source_draft_version,
                key_request_ids=key_request_ids,
                noise_request_ids=noise_request_ids,
                field_descriptions=field_descriptions,
                parameter_source_map=parameter_source_map,
                action_stage_ids=action_stage_ids,
                risk_flags=risk_flags,
            )
        else:
            reviewed = latest_chain_item.next_version(
                reviewer=reviewer,
                source_draft_version=source_draft_version,
                key_request_ids=key_request_ids,
                noise_request_ids=noise_request_ids,
                field_descriptions=field_descriptions,
                parameter_source_map=parameter_source_map,
                action_stage_ids=action_stage_ids,
                risk_flags=risk_flags,
            )

        updated_aggregate = replace(
            aggregate,
            reviewed_metadata=(*aggregate.reviewed_metadata, reviewed),
        )
        self._recording_repository.save(updated_aggregate)
        return reviewed

    def latest_reviewed_metadata(
        self,
        aggregate: RecordingAggregate,
    ) -> ReviewedMetadata | None:
        if not aggregate.reviewed_metadata:
            return None
        return aggregate.reviewed_metadata[-1]

    def review_history(
        self,
        aggregate: RecordingAggregate,
    ) -> tuple[ReviewedMetadata, ...]:
        return tuple(sorted(aggregate.reviewed_metadata, key=lambda item: item.version, reverse=True))

    def latest_draft(self, aggregate: RecordingAggregate) -> MetadataDraft | None:
        if not aggregate.metadata_drafts:
            return None
        return aggregate.metadata_drafts[-1]

    def _find_draft(
        self,
        aggregate: RecordingAggregate,
        *,
        source_draft_id: str,
        source_draft_version: int,
    ) -> MetadataDraft | None:
        for item in aggregate.metadata_drafts:
            if item.id == source_draft_id and item.version == source_draft_version:
                return item
        return None

    def _latest_review_for_draft(
        self,
        aggregate: RecordingAggregate,
        *,
        source_draft_id: str,
    ) -> ReviewedMetadata | None:
        for item in reversed(aggregate.reviewed_metadata):
            if item.source_draft_id == source_draft_id:
                return item
        return None
