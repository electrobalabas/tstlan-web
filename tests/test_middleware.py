import asyncio
from collections.abc import Iterator
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.service import create_session, create_user
from tstlan.config import Settings
from tstlan.db import create_engine, create_sessionmaker, init_db

ALLOWED_ORIGIN = "http://app.test"
FOREIGN_ORIGIN = "http://evil.test"


async def _seed(url: str) -> tuple[str, str]:
    engine = create_engine(url)
    await init_db(engine)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as db:
        user = await create_user(db, login="alice", password="pw")
        created = await create_session(db, user, ttl=timedelta(hours=720))
        token, csrf = created.token, created.csrf_token
    await engine.dispose()
    return token, csrf


@pytest.fixture
def client_token_csrf(tmp_path: Path) -> Iterator[tuple[TestClient, str, str]]:
    url = f"sqlite+aiosqlite:///{tmp_path / 'auth.db'}"
    token, csrf = asyncio.run(_seed(url))
    app = create_app(
        settings=Settings(database_url=url, allowed_origins=[ALLOWED_ORIGIN])
    )

    @app.post("/echo")
    def _echo() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/auth/login")
    def _login() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        client.cookies.set("tstlan_session", token)
        yield client, token, csrf


def test_safe_request_refreshes_session_cookie(
    client_token_csrf: tuple[TestClient, str, str],
) -> None:
    client, _token, _csrf = client_token_csrf
    response = client.get("/health")
    assert "tstlan_session" in response.headers.get("set-cookie", "")


def test_unsafe_request_with_valid_csrf_passes(
    client_token_csrf: tuple[TestClient, str, str],
) -> None:
    client, _token, csrf = client_token_csrf
    response = client.post(
        "/echo", headers={"Origin": ALLOWED_ORIGIN, "X-CSRF-Token": csrf}
    )
    assert response.status_code == 200


def test_unsafe_request_without_csrf_token_is_rejected(
    client_token_csrf: tuple[TestClient, str, str],
) -> None:
    client, _token, _csrf = client_token_csrf
    response = client.post("/echo", headers={"Origin": ALLOWED_ORIGIN})
    assert response.status_code == 403


def test_unsafe_request_from_foreign_origin_is_rejected(
    client_token_csrf: tuple[TestClient, str, str],
) -> None:
    client, _token, csrf = client_token_csrf
    response = client.post(
        "/echo", headers={"Origin": FOREIGN_ORIGIN, "X-CSRF-Token": csrf}
    )
    assert response.status_code == 403


def test_anonymous_unsafe_request_reaches_endpoint(
    client_token_csrf: tuple[TestClient, str, str],
) -> None:
    client, _token, _csrf = client_token_csrf
    client.cookies.clear()
    response = client.post("/echo", headers={"Origin": ALLOWED_ORIGIN})
    assert response.status_code == 200


def test_login_rejects_foreign_origin(
    client_token_csrf: tuple[TestClient, str, str],
) -> None:
    client, _token, _csrf = client_token_csrf
    client.cookies.clear()
    response = client.post("/auth/login", headers={"Origin": FOREIGN_ORIGIN})
    assert response.status_code == 403


def test_login_allows_known_origin_without_csrf(
    client_token_csrf: tuple[TestClient, str, str],
) -> None:
    client, _token, _csrf = client_token_csrf
    client.cookies.clear()
    response = client.post("/auth/login", headers={"Origin": ALLOWED_ORIGIN})
    assert response.status_code == 200
