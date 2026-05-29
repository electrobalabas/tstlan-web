from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


def create_engine(database_url: str) -> AsyncEngine:
    url = make_url(database_url)
    kwargs: dict[str, Any] = {}
    if url.get_backend_name() == "sqlite" and url.database in (None, "", ":memory:"):
        # In-memory SQLite is private to a single connection; pin one shared
        # connection so the schema created at startup is visible to every session.
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(url, **kwargs)
    if url.get_backend_name() == "sqlite":
        _enable_sqlite_foreign_keys(engine)
    return engine


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
    # SQLite ignores foreign keys unless asked per connection; Postgres enforces
    # them natively, so this is scoped to the SQLite dialect.
    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
