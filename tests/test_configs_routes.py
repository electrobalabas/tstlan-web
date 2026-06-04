import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.auth.service import create_user
from tstlan.config import Settings
from tstlan.db import create_engine, create_sessionmaker, init_db

ORIGIN = "http://app.test"


async def _seed(url: str) -> None:
    engine = create_engine(url)
    await init_db(engine)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as db:
        await create_user(db, login="dev", password="pw", role=Role.DEV)
        await create_user(db, login="bob", password="pw", role=Role.USER)
        await create_user(db, login="root", password="pw", role=Role.ADMIN)
    await engine.dispose()


class Caller:
    """Залогиненный клиент с CSRF-токеном для безопасных мутаций."""

    def __init__(self, app: Any, login: str) -> None:
        self.http = TestClient(app)
        body = self.http.post(
            "/auth/login",
            json={"login": login, "password": "pw"},
            headers={"Origin": ORIGIN},
        ).json()
        self._headers = {"Origin": ORIGIN, "X-CSRF-Token": body["csrf_token"]}

    def get(self, url: str) -> httpx.Response:
        return self.http.get(url)

    def post(self, url: str, json: dict[str, Any]) -> httpx.Response:
        return self.http.post(url, json=json, headers=self._headers)

    def put(self, url: str, json: dict[str, Any]) -> httpx.Response:
        return self.http.put(url, json=json, headers=self._headers)

    def delete(self, url: str) -> httpx.Response:
        return self.http.delete(url, headers=self._headers)


@pytest.fixture
def app(tmp_path: Path) -> Iterator[Any]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'configs.db'}"
    asyncio.run(_seed(url))
    yield create_app(settings=Settings(database_url=url, allowed_origins=[ORIGIN]))


def _make_payload(name: str = "cfg", **extra: Any) -> dict[str, Any]:
    return {"name": name, "device_type": "multimeter", **extra}


def test_requires_authentication(app: Any) -> None:
    assert TestClient(app).get("/configs").status_code == 401


def test_create_returns_owner_detail(app: Any) -> None:
    dev = Caller(app, "dev")
    body = dev.post("/configs", _make_payload()).json()
    assert body["access"] == "owner"
    assert body["owner_login"] == "dev"
    assert body["visibility"] == "private"


def test_user_cannot_publish(app: Any) -> None:
    bob = Caller(app, "bob")
    response = bob.post("/configs", _make_payload(visibility="public"))
    assert response.status_code == 403


def test_public_config_is_listed_and_read_only_for_others(app: Any) -> None:
    dev = Caller(app, "dev")
    config_id = dev.post("/configs", _make_payload(visibility="public")).json()["id"]

    bob = Caller(app, "bob")
    listing = bob.get("/configs").json()
    assert [c["id"] for c in listing] == [config_id]

    detail = bob.get(f"/configs/{config_id}").json()
    assert detail["access"] == "read"
    # Гранты видны только управляющему конфигом.
    assert detail["shares"] == []

    denied = bob.put(f"/configs/{config_id}", {"name": "x"})
    assert denied.status_code == 403


def test_write_share_allows_payload_edit_not_rename(app: Any) -> None:
    dev = Caller(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    dev.post(f"/configs/{config_id}/shares", {"login": "bob", "permission": "write"})

    bob = Caller(app, "bob")
    payload = {
        "connection": {"transport": "ethernet", "poll_period_ms": 200},
        "variables": [
            {"name": "voltage", "ctype": "f32", "graph": True, "category": ""}
        ],
    }
    edited = bob.put(f"/configs/{config_id}", {"payload": payload})
    assert edited.status_code == 200
    assert edited.json()["payload"]["variables"][0]["name"] == "voltage"

    renamed = bob.put(f"/configs/{config_id}", {"name": "stolen"})
    assert renamed.status_code == 403


def test_share_makes_config_shared_and_visible_to_grantee(app: Any) -> None:
    dev = Caller(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    shared = dev.post(
        f"/configs/{config_id}/shares", {"login": "bob", "permission": "read"}
    ).json()
    assert shared["visibility"] == "shared"
    assert {"login": "bob", "permission": "read"} in shared["shares"]

    bob = Caller(app, "bob")
    assert bob.get(f"/configs/{config_id}").status_code == 200


def test_share_with_unknown_login_is_not_found(app: Any) -> None:
    dev = Caller(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    response = dev.post(f"/configs/{config_id}/shares", {"login": "ghost"})
    assert response.status_code == 404


def test_only_owner_deletes(app: Any) -> None:
    dev = Caller(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    dev.post(f"/configs/{config_id}/shares", {"login": "bob", "permission": "write"})

    bob = Caller(app, "bob")
    assert bob.delete(f"/configs/{config_id}").status_code == 403
    assert dev.delete(f"/configs/{config_id}").status_code == 204
    assert dev.get(f"/configs/{config_id}").status_code == 404


def test_admin_sees_and_manages_foreign_config(app: Any) -> None:
    dev = Caller(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]

    root = Caller(app, "root")
    detail = root.get(f"/configs/{config_id}").json()
    assert detail["access"] == "owner"
    assert root.delete(f"/configs/{config_id}").status_code == 204
