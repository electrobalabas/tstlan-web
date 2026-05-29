import sqlite3
from pathlib import Path

from tstlan.db import run_migrations


def test_migrations_create_the_expected_schema(tmp_path: Path) -> None:
    db_file = tmp_path / "tstlan.db"
    run_migrations(f"sqlite+aiosqlite:///{db_file}")
    assert _tables(db_file) == {"users", "sessions", "alembic_version"}


def _tables(db_file: Path) -> set[str]:
    con = sqlite3.connect(db_file)
    query = "select name from sqlite_master where type='table'"
    try:
        return {
            name for (name,) in con.execute(query) if not name.startswith("sqlite_")
        }
    finally:
        con.close()
