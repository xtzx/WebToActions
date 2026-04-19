from datetime import UTC, datetime
from enum import StrEnum

from typing import Self

from pydantic import Field, model_validator

from app.core.domain_model import DomainModel


class RecordingStatus(StrEnum):
    CREATED = "created"
    RECORDING = "recording"
    PENDING_REVIEW = "pending_review"
    MACRO_GENERATED = "macro_generated"


class Recording(DomainModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    start_url: str = Field(min_length=1)
    browser_session_id: str = Field(min_length=1)
    status: RecordingStatus = RecordingStatus.CREATED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    ended_at: datetime | None = None
    generated_action_macro_id: str | None = None

    @model_validator(mode="after")
    def validate_macro_generated_state(self) -> Self:
        if (
            self.status == RecordingStatus.MACRO_GENERATED
            and not self.generated_action_macro_id
        ):
            raise ValueError(
                "generated_action_macro_id is required when status is macro_generated.",
            )

        return self

    @model_validator(mode="after")
    def validate_state_shape(self) -> Self:
        if self.status != RecordingStatus.CREATED and self.started_at is None:
            raise ValueError("started_at is required once recording has started.")

        if (
            self.status in {RecordingStatus.PENDING_REVIEW, RecordingStatus.MACRO_GENERATED}
            and self.ended_at is None
        ):
            raise ValueError("ended_at is required once recording has finished.")

        if (
            self.status != RecordingStatus.MACRO_GENERATED
            and self.generated_action_macro_id is not None
        ):
            raise ValueError(
                "generated_action_macro_id is only allowed for macro_generated recordings.",
            )

        if (
            self.started_at is not None
            and self.ended_at is not None
            and self.ended_at < self.started_at
        ):
            raise ValueError("ended_at cannot be earlier than started_at.")

        return self

    def _transition(
        self,
        *,
        allowed_from: set[RecordingStatus],
        next_status: RecordingStatus,
        **changes: object,
    ) -> Self:
        if self.status not in allowed_from:
            raise ValueError(
                f"Cannot transition recording from {self.status.value} "
                f"to {next_status.value}.",
            )

        return self.validated_copy(status=next_status, **changes)

    def start(self) -> Self:
        return self._transition(
            allowed_from={RecordingStatus.CREATED},
            next_status=RecordingStatus.RECORDING,
            started_at=datetime.now(UTC),
        )

    def finish(self) -> Self:
        return self._transition(
            allowed_from={RecordingStatus.RECORDING},
            next_status=RecordingStatus.PENDING_REVIEW,
            ended_at=datetime.now(UTC),
        )

    def mark_macro_generated(self, *, action_macro_id: str) -> Self:
        if not action_macro_id:
            raise ValueError("action_macro_id is required when macro generation completes.")

        if self.status != RecordingStatus.PENDING_REVIEW:
            raise ValueError(
                "Recording must be pending_review before macro generation.",
            )

        return self._transition(
            allowed_from={RecordingStatus.PENDING_REVIEW},
            next_status=RecordingStatus.MACRO_GENERATED,
            generated_action_macro_id=action_macro_id,
        )
