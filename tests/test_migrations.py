import json
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

from tstlan.db import run_migrations


def test_migrations_create_the_expected_schema(tmp_path: Path) -> None:
    db_file = tmp_path / "tstlan.db"
    run_migrations(f"sqlite+aiosqlite:///{db_file}")
    assert _tables(db_file) == {
        "users",
        "sessions",
        "device_configs",
        "config_shares",
        "alembic_version",
    }


def test_migration_normalizes_transport_and_drops_variable_index(
    tmp_path: Path,
) -> None:
    db_file = tmp_path / "tstlan.db"
    config = _alembic_config(f"sqlite+aiosqlite:///{db_file}")
    command.upgrade(config, "a1b2c3d4e5f6")

    # Легаси-payload: старый транспорт modbus и разрежённые адреса в `index`.
    payload = json.dumps(
        {
            "connection": {"transport": "modbus"},
            "variables": [
                {
                    "index": 0,
                    "name": "a",
                    "ctype": "bit",
                    "graph": False,
                    "category": "",
                },
                {
                    "index": 34,
                    "name": "b",
                    "ctype": "u8",
                    "graph": False,
                    "category": "",
                },
            ],
        }
    )
    con = sqlite3.connect(db_file)
    con.execute(
        "insert into users (login, password_hash, role, is_active, created_at) "
        "values ('owner', 'x', 'dev', 1, '2026-01-01')"
    )
    con.execute(
        "insert into device_configs "
        "(owner_id, name, device_type, payload, visibility, created_at, updated_at) "
        "values (1, 'cfg', 'dev', ?, 'private', '2026-01-01', '2026-01-01')",
        (payload,),
    )
    con.commit()
    con.close()

    command.upgrade(config, "head")

    con = sqlite3.connect(db_file)
    try:
        stored = json.loads(
            con.execute("select payload from device_configs").fetchone()[0]
        )
    finally:
        con.close()
    assert stored["connection"]["transport"] == "modbus_tcp"
    assert [variable["name"] for variable in stored["variables"]] == ["a", "b"]
    assert all("index" not in variable for variable in stored["variables"])

    command.downgrade(config, "a1b2c3d4e5f6")
    con = sqlite3.connect(db_file)
    try:
        reverted = json.loads(
            con.execute("select payload from device_configs").fetchone()[0]
        )
    finally:
        con.close()
    assert reverted["connection"]["transport"] == "modbus"
    # Исходные адреса не восстановить — индекс раскладывается по позиции.
    assert [variable["index"] for variable in reverted["variables"]] == [0, 1]


def _alembic_config(url: str) -> Config:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def _tables(db_file: Path) -> set[str]:
    con = sqlite3.connect(db_file)
    query = "select name from sqlite_master where type='table'"
    try:
        return {
            name for (name,) in con.execute(query) if not name.startswith("sqlite_")
        }
    finally:
        con.close()
