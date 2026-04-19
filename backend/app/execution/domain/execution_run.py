from datetime import UTC, datetime
from typing import Any
from typing import Self

from enum import StrEnum

from pydantic import Field, model_validator

from app.action.domain.action_kind import ActionKind
from app.core.domain_model import DomainModel

ExecutableActionKind = ActionKind


class ExecutionRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class ExecutionRun(DomainModel):
    id: str = Field(min_length=1)
    action_kind: ActionKind
    action_id: str = Field(min_length=1)
    action_version: int = Field(ge=1)
    browser_session_id: str = Field(min_length=1)
    parameters_snapshot: dict[str, Any] = Field(default_factory=dict)
    status: ExecutionRunStatus = ExecutionRunStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    ended_at: datetime | None = None
    step_logs: list[str] = Field(default_factory=list)
    failure_reason: str | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_state_shape(self) -> Self:
        if self.status != ExecutionRunStatus.PENDING and self.started_at is None:
            raise ValueError("started_at is required once execution run has started.")

        if (
            self.status in {ExecutionRunStatus.SUCCEEDED, ExecutionRunStatus.FAILED}
            and self.ended_at is None
        ):
            raise ValueError("ended_at is required for terminal execution run states.")

        if self.status == ExecutionRunStatus.FAILED and not self.failure_reason:
            raise ValueError("failure_reason is required when execution run has failed.")

        if self.status != ExecutionRunStatus.FAILED and self.failure_reason is not None:
            raise ValueError(
                "failure_reason is only allowed for failed execution runs.",
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
        allowed_from: set[ExecutionRunStatus],
        next_status: ExecutionRunStatus,
        **changes: Any,
    ) -> Self:
        if self.status not in allowed_from:
            raise ValueError(
                f"Cannot transition execution run from {self.status.value} "
                f"to {next_status.value}; current state is terminal or invalid.",
            )

        return self.validated_copy(status=next_status, **changes)

    def start(self) -> Self:
        return self._transition(
            allowed_from={ExecutionRunStatus.PENDING},
            next_status=ExecutionRunStatus.RUNNING,
            started_at=datetime.now(UTC),
        )

    def succeed(self) -> Self:
        return self._transition(
            allowed_from={ExecutionRunStatus.RUNNING},
            next_status=ExecutionRunStatus.SUCCEEDED,
            ended_at=datetime.now(UTC),
            failure_reason=None,
        )

    def fail(self, reason: str) -> Self:
        if not reason.strip():
            raise ValueError("reason is required when marking an execution run as failed.")

        return self._transition(
            allowed_from={ExecutionRunStatus.RUNNING},
            next_status=ExecutionRunStatus.FAILED,
            ended_at=datetime.now(UTC),
            failure_reason=reason,
        )
