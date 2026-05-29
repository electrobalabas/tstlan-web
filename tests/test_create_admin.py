import sqlite3
from pathlib import Path

import pytest

from tstlan.tools.create_admin import main


def test_create_admin_cli(tmp_path: Path) -> None:
    db_file = tmp_path / "tstlan.db"
    main(["--login", "root", "--password", "pw", "--database-url", _url(db_file)])

    con = sqlite3.connect(db_file)
    try:
        rows = con.execute("SELECT login, role FROM users").fetchall()
    finally:
        con.close()
    assert rows == [("root", "admin")]


def test_create_admin_rejects_duplicate(tmp_path: Path) -> None:
    db_file = tmp_path / "tstlan.db"
    main(["--login", "root", "--password", "pw", "--database-url", _url(db_file)])

    with pytest.raises(SystemExit):
        main(["--login", "root", "--password", "pw2", "--database-url", _url(db_file)])


def _url(db_file: Path) -> str:
    return f"sqlite+aiosqlite:///{db_file}"
