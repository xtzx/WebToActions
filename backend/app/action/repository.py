from typing import Protocol

from sqlalchemy.orm import Session

from app.action.domain import ActionMacro


class ActionMacroRepository(Protocol):
    def save(self, item: ActionMacro, *, session: Session | None = None) -> None:
        """Persist one action macro version."""

    def get(self, action_id: str, version: int | None = None) -> ActionMacro | None:
        """Load one action macro by id and optional version."""

    def list(self) -> tuple[ActionMacro, ...]:
        """List the latest version of each action macro."""
