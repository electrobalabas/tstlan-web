from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.config import Settings


@pytest.fixture
def client(sqlite_url, seed_users, allowed_origin: str) -> Iterator[TestClient]:
    url = sqlite_url("auth.db")
    seed_users(url, [("alice", Role.USER)])
    app = create_app(
        settings=Settings(database_url=url, allowed_origins=[allowed_origin])
    )
    with TestClient(app) as test_client:
        yield test_client


def _login(client: TestClient, origin: str) -> httpx.Response:
    return client.post(
        "/auth/login",
        json={"login": "alice", "password": "pw"},
        headers={"Origin": origin},
    )


def test_login_returns_user_identity_with_csrf(
    client: TestClient, allowed_origin: str
) -> None:
    body = _login(client, allowed_origin).json()
    assert {
        "login": body["login"],
        "role": body["role"],
        "has_csrf": bool(body.get("csrf_token")),
    } == {"login": "alice", "role": "user", "has_csrf": True}


def test_login_sets_session_cookie(client: TestClient, allowed_origin: str) -> None:
    response = _login(client, allowed_origin)
    assert "tstlan_session" in response.headers.get("set-cookie", "")


def test_login_rejected_from_foreign_origin(
    client: TestClient, foreign_origin: str
) -> None:
    response = client.post(
        "/auth/login",
        json={"login": "alice", "password": "pw"},
        headers={"Origin": foreign_origin},
    )
    assert response.status_code == 403


def test_login_rejects_wrong_password(client: TestClient, allowed_origin: str) -> None:
    response = client.post(
        "/auth/login",
        json={"login": "alice", "password": "nope"},
        headers={"Origin": allowed_origin},
    )
    assert response.status_code == 401


def test_me_returns_current_user(client: TestClient, allowed_origin: str) -> None:
    _login(client, allowed_origin)
    body = client.get("/auth/me").json()
    assert {"login": body["login"], "role": body["role"]} == {
        "login": "alice",
        "role": "user",
    }


def test_me_requires_authentication(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_logout_revokes_the_session(client: TestClient, allowed_origin: str) -> None:
    csrf = _login(client, allowed_origin).json()["csrf_token"]
    client.post(
        "/auth/logout", headers={"Origin": allowed_origin, "X-CSRF-Token": csrf}
    )
    assert client.get("/auth/me").status_code == 401


def test_users_listing_requires_authentication(client: TestClient) -> None:
    assert client.get("/users").status_code == 401


def test_users_listing_returns_login_and_role(
    client: TestClient, allowed_origin: str
) -> None:
    _login(client, allowed_origin)
    assert client.get("/users").json() == [{"login": "alice", "role": "user"}]
