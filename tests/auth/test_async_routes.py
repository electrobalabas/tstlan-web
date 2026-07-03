from collections.abc import AsyncIterator

import httpx
import pytest

from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.auth.service import create_user
from tstlan.config import Settings
from tstlan.db import create_engine, create_sessionmaker, init_db

pytestmark = pytest.mark.anyio


@pytest.fixture
async def async_auth_client(
    sqlite_url, allowed_origin: str
) -> AsyncIterator[httpx.AsyncClient]:
    database_url = sqlite_url("async-auth.db")
    seed_engine = create_engine(database_url)
    await init_db(seed_engine)
    sessionmaker = create_sessionmaker(seed_engine)
    async with sessionmaker() as db:
        await create_user(db, login="alice", password="pw", role=Role.USER)
    await seed_engine.dispose()

    app = create_app(
        settings=Settings(database_url=database_url, allowed_origins=[allowed_origin])
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://app.test",
        headers={"Origin": allowed_origin},
    ) as client:
        yield client
    await app.state.engine.dispose()


async def test_async_login_me_and_logout_flow(
    async_auth_client: httpx.AsyncClient,
) -> None:
    login = await async_auth_client.post(
        "/auth/login", json={"login": "alice", "password": "pw"}
    )
    assert login.status_code == 200
    body = login.json()
    assert {"login": body["login"], "role": body["role"]} == {
        "login": "alice",
        "role": "user",
    }

    me = await async_auth_client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["login"] == "alice"

    logout = await async_auth_client.post(
        "/auth/logout", headers={"X-CSRF-Token": body["csrf_token"]}
    )
    assert logout.status_code == 200
    assert (await async_auth_client.get("/auth/me")).status_code == 401
