from typing import Protocol

from sqlalchemy.orm import Session

from app.execution.domain.execution_run import ExecutionRun


class ExecutionRunRepository(Protocol):
    def save(self, item: ExecutionRun, *, session: Session | None = None) -> None:
        """Persist one execution run."""

    def get(self, execution_id: str) -> ExecutionRun | None:
        """Load one execution run."""

    def list(self) -> tuple[ExecutionRun, ...]:
        """List persisted execution runs."""
