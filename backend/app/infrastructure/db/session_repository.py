from datetime import UTC, datetime

from sqlalchemy import insert, select, update
from sqlalchemy.orm import Session, sessionmaker

from app.infrastructure.db.schema import browser_session
from app.session.domain.browser_session import BrowserSession


class SqliteBrowserSessionRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def save(self, item: BrowserSession) -> None:
        with self._session_factory.begin() as session:
            row = self._row(item)
            existing = session.execute(
                select(browser_session.c.id).where(browser_session.c.id == item.id)
            ).first()
            if existing is None:
                session.execute(insert(browser_session).values(row))
            else:
                session.execute(
                    update(browser_session)
                    .where(browser_session.c.id == item.id)
                    .values(row)
                )

    def get(self, session_id: str) -> BrowserSession | None:
        with self._session_factory() as session:
            row = session.execute(
                select(browser_session).where(browser_session.c.id == session_id)
            ).mappings().first()
            if row is None:
                return None
            return self._load(row)

    def list(self) -> tuple[BrowserSession, ...]:
        with self._session_factory() as session:
            rows = session.execute(
                select(browser_session).order_by(browser_session.c.created_at.desc())
            ).mappings()
            return tuple(self._load(row) for row in rows)

    def _row(self, item: BrowserSession) -> dict[str, object]:
        payload = item.model_dump()
        return {
            "id": payload["id"],
            "profile_id": payload["profile_id"],
            "status": payload["status"],
            "login_site_summaries_json": payload["login_site_summaries"],
            "created_at": item.created_at,
            "last_activity_at": item.last_activity_at,
        }

    def _load(self, row) -> BrowserSession:  # type: ignore[no-untyped-def]
        return BrowserSession(
            id=row["id"],
            profile_id=row["profile_id"],
            status=row["status"],
            login_site_summaries=row["login_site_summaries_json"],
            created_at=_ensure_utc(row["created_at"]),
            last_activity_at=_ensure_utc(row["last_activity_at"]),
        )


def _ensure_utc(value: datetime | None) -> datetime | None:
    if value is None or value.tzinfo is not None:
        return value

    return value.replace(tzinfo=UTC)
