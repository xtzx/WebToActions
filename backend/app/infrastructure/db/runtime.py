from dataclasses import dataclass
from pathlib import Path
import sqlite3

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import REPO_ROOT


@dataclass(frozen=True)
class SqliteRuntime:
    database_path: Path
    database_url: str
    engine: Engine
    session_factory: sessionmaker[Session]


def sqlite_database_url(database_path: Path) -> str:
    return f"sqlite:///{database_path}"


def initialize_sqlite_runtime(database_path: Path) -> SqliteRuntime:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_url = sqlite_database_url(database_path)
    command.upgrade(_build_alembic_config(database_url), "head")
    engine = create_engine(database_url, future=True)
    _enable_sqlite_foreign_keys(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return SqliteRuntime(
        database_path=database_path,
        database_url=database_url,
        engine=engine,
        session_factory=session_factory,
    )


def _build_alembic_config(database_url: str) -> Config:
    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "backend" / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _enable_sqlite_foreign_keys(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
