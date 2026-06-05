import asyncio
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.service import create_user
from tstlan.config import Settings
from tstlan.db import create_engine, create_sessionmaker, init_db

ORIGIN = "http://app.test"
FOREIGN_ORIGIN = "http://evil.test"
CREDENTIALS = {"login": "alice", "password": "pw"}


async def _seed_user(url: str) -> None:
    engine = create_engine(url)
    await init_db(engine)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as db:
        await create_user(db, login="alice", password="pw")
    await engine.dispose()


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}"
    asyncio.run(_seed_user(url))
    app = create_app(settings=Settings(database_url=url, allowed_origins=[ORIGIN]))
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient) -> httpx.Response:
    return client.post("/auth/login", json=CREDENTIALS, headers={"Origin": ORIGIN})


def test_login_returns_user_identity_with_csrf(client: TestClient) -> None:
    body = _login(client).json()
    assert {
        "login": body["login"],
        "role": body["role"],
        "has_csrf": bool(body.get("csrf_token")),
    } == {"login": "alice", "role": "user", "has_csrf": True}


def test_login_sets_session_cookie(client: TestClient) -> None:
    response = _login(client)
    assert "tstlan_session" in response.headers.get("set-cookie", "")


def test_login_rejected_from_foreign_origin(client: TestClient) -> None:
    response = client.post(
        "/auth/login", json=CREDENTIALS, headers={"Origin": FOREIGN_ORIGIN}
    )
    assert response.status_code == 403


def test_login_rejects_wrong_password(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"login": "alice", "password": "nope"},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient) -> None:
    _login(client)
    body = client.get("/auth/me").json()
    assert {"login": body["login"], "role": body["role"]} == {
        "login": "alice",
        "role": "user",
    }


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_logout_revokes_the_session(client: TestClient) -> None:
    csrf = _login(client).json()["csrf_token"]
    client.post("/auth/logout", headers={"Origin": ORIGIN, "X-CSRF-Token": csrf})
    assert client.get("/auth/me").status_code == 401


def test_users_listing_requires_authentication(client: TestClient) -> None:
    assert client.get("/users").status_code == 401


def test_users_listing_returns_login_and_role(client: TestClient) -> None:
    _login(client)
    assert client.get("/users").json() == [{"login": "alice", "role": "user"}]
