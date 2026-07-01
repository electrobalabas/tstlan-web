import sqlite3
from pathlib import Path

import pytest

from tstlan.tools.create_admin import main


def test_create_admin_persists_an_admin(tmp_path: Path) -> None:
    db_file = tmp_path / "tstlan.db"
    main(["--login", "root", "--password", "pw", "--database-url", _url(db_file)])
    assert _users(db_file) == [("root", "admin")]


def test_create_admin_rejects_existing_login(tmp_path: Path) -> None:
    db_file = tmp_path / "tstlan.db"
    main(["--login", "root", "--password", "pw", "--database-url", _url(db_file)])
    with pytest.raises(SystemExit):
        main(["--login", "root", "--password", "pw2", "--database-url", _url(db_file)])


def _url(db_file: Path) -> str:
    return f"sqlite+aiosqlite:///{db_file}"


def _users(db_file: Path) -> list[tuple[str, str]]:
    con = sqlite3.connect(db_file)
    try:
        return con.execute("select login, role from users").fetchall()
    finally:
        con.close()
