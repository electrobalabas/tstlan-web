import os

import psycopg
import pytest
from sqlalchemy.engine import make_url

from tstlan.db import run_migrations


pytestmark = pytest.mark.postgres

TEST_DATABASE_URL_ENV = "TEST_POSTGRES_DATABASE_URL"
EXPECTED_TABLES = {
    "users",
    "sessions",
    "device_configs",
    "config_shares",
    "alembic_version",
}


def test_migrations_create_expected_schema_on_postgres() -> None:
    database_url = os.environ.get(TEST_DATABASE_URL_ENV)
    if not database_url:
        pytest.skip(f"{TEST_DATABASE_URL_ENV} is not set")

    _reset_public_schema(database_url)
    run_migrations(database_url)

    assert _tables(database_url) == EXPECTED_TABLES


def _reset_public_schema(database_url: str) -> None:
    with psycopg.connect(_sync_database_url(database_url), autocommit=True) as conn:
        conn.execute("drop schema if exists public cascade")
        conn.execute("create schema public")


def _tables(database_url: str) -> set[str]:
    with psycopg.connect(_sync_database_url(database_url)) as conn:
        rows = conn.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public'
              and table_type = 'BASE TABLE'
            """
        )
        return {table_name for (table_name,) in rows}


def _sync_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if "+" in url.drivername:
        url = url.set(drivername=url.drivername.split("+", maxsplit=1)[0])
    return url.render_as_string(hide_password=False)
