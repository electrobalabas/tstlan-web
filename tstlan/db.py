import logging
from pathlib import Path
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

from tstlan.logging_setup import get_service_logger, log_event

logger = get_service_logger("db")


class Base(DeclarativeBase):
    pass


def create_engine(database_url: str) -> AsyncEngine:
    url = make_url(database_url)
    kwargs: dict[str, Any] = {}
    if url.get_backend_name() == "sqlite" and url.database in (None, "", ":memory:"):
        kwargs["poolclass"] = StaticPool
        kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_async_engine(url, **kwargs)
    log_event(
        logger,
        logging.INFO,
        "db.engine.created",
        backend=url.get_backend_name(),
        driver=url.get_driver_name(),
        database=url.database,
    )
    if url.get_backend_name() == "sqlite":
        _enable_sqlite_foreign_keys(engine)
    return engine


def _enable_sqlite_foreign_keys(engine: AsyncEngine) -> None:
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


def run_migrations(database_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parent.parent
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(config, "head")
    url = make_url(database_url)
    log_event(
        logger,
        logging.INFO,
        "db.migrations.applied",
        backend=url.get_backend_name(),
        database=url.database,
    )
