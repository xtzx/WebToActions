from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.infrastructure.db.session_repository import SqliteBrowserSessionRepository
from app.session.domain.browser_session import BrowserSession


class BrowserSessionManager:
    def __init__(
        self,
        *,
        repository: SqliteBrowserSessionRepository,
        profiles_root: Path,
    ) -> None:
        self._repository = repository
        self._profiles_root = profiles_root
        self._profiles_root.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> tuple[BrowserSession, ...]:
        return self._repository.list()

    def create_session(self) -> BrowserSession:
        session_id = f"session-{uuid4().hex[:8]}"
        session = BrowserSession(
            id=session_id,
            profile_id=f"profile-{session_id}",
        )
        self._repository.save(session)
        self.profile_dir(session.profile_id)
        return session

    def get_session(self, session_id: str) -> BrowserSession | None:
        return self._repository.get(session_id)

    def ensure_session(self, session_id: str | None) -> BrowserSession:
        if session_id is None:
            return self.create_session()

        session = self.get_session(session_id)
        if session is None:
            raise KeyError(f"Browser session {session_id} does not exist.")
        return session

    def update_session_activity(
        self,
        session: BrowserSession,
        *,
        login_site_summaries: list[str],
    ) -> BrowserSession:
        updated = session.validated_copy(
            login_site_summaries=login_site_summaries,
            last_activity_at=datetime.now(UTC),
        )
        self._repository.save(updated)
        return updated

    def profile_dir(self, profile_id: str) -> Path:
        path = self._profiles_root / profile_id
        path.mkdir(parents=True, exist_ok=True)
        return path
