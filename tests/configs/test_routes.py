from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.config import Settings


@pytest.fixture
def app(sqlite_url, seed_users, allowed_origin: str) -> Iterator[Any]:
    url = sqlite_url("configs.db")
    seed_users(url, [("dev", Role.DEV), ("bob", Role.USER), ("root", Role.ADMIN)])
    yield create_app(
        settings=Settings(database_url=url, allowed_origins=[allowed_origin])
    )


def _make_payload(name: str = "cfg", **extra: Any) -> dict[str, Any]:
    return {"name": name, "device_type": "multimeter", **extra}


def test_requires_authentication(app: Any) -> None:
    assert TestClient(app).get("/configs").status_code == 401


def test_create_returns_owner_detail(app: Any, authenticated_client) -> None:
    dev = authenticated_client(app, "dev")
    body = dev.post("/configs", _make_payload()).json()
    assert body["access"] == "owner"
    assert body["owner_login"] == "dev"
    assert body["visibility"] == "private"


def test_user_cannot_publish(app: Any, authenticated_client) -> None:
    bob = authenticated_client(app, "bob")
    response = bob.post("/configs", _make_payload(visibility="public"))
    assert response.status_code == 403


def test_public_config_is_listed_and_read_only_for_others(
    app: Any, authenticated_client
) -> None:
    dev = authenticated_client(app, "dev")
    config_id = dev.post("/configs", _make_payload(visibility="public")).json()["id"]

    bob = authenticated_client(app, "bob")
    listing = bob.get("/configs").json()
    assert [c["id"] for c in listing] == [config_id]

    detail = bob.get(f"/configs/{config_id}").json()
    assert detail["access"] == "read"
    # Гранты видны только управляющему конфигом.
    assert detail["shares"] == []

    denied = bob.put(f"/configs/{config_id}", {"name": "x"})
    assert denied.status_code == 403


def test_write_share_allows_payload_edit_not_rename(
    app: Any, authenticated_client
) -> None:
    dev = authenticated_client(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    dev.post(f"/configs/{config_id}/shares", {"login": "bob", "permission": "write"})

    bob = authenticated_client(app, "bob")
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


def test_share_makes_config_shared_and_visible_to_grantee(
    app: Any, authenticated_client
) -> None:
    dev = authenticated_client(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    shared = dev.post(
        f"/configs/{config_id}/shares", {"login": "bob", "permission": "read"}
    ).json()
    assert shared["visibility"] == "shared"
    assert {"login": "bob", "permission": "read"} in shared["shares"]

    bob = authenticated_client(app, "bob")
    assert bob.get(f"/configs/{config_id}").status_code == 200


def test_reshare_updates_permission(app: Any, authenticated_client) -> None:
    dev = authenticated_client(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    dev.post(f"/configs/{config_id}/shares", {"login": "bob", "permission": "read"})
    updated = dev.post(
        f"/configs/{config_id}/shares", {"login": "bob", "permission": "write"}
    )
    assert updated.status_code == 200
    assert {"login": "bob", "permission": "write"} in updated.json()["shares"]


def test_share_with_unknown_login_is_not_found(app: Any, authenticated_client) -> None:
    dev = authenticated_client(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    response = dev.post(f"/configs/{config_id}/shares", {"login": "ghost"})
    assert response.status_code == 404


def test_only_owner_deletes(app: Any, authenticated_client) -> None:
    dev = authenticated_client(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]
    dev.post(f"/configs/{config_id}/shares", {"login": "bob", "permission": "write"})

    bob = authenticated_client(app, "bob")
    assert bob.delete(f"/configs/{config_id}").status_code == 403
    assert dev.delete(f"/configs/{config_id}").status_code == 204
    assert dev.get(f"/configs/{config_id}").status_code == 404


def test_admin_sees_and_manages_foreign_config(app: Any, authenticated_client) -> None:
    dev = authenticated_client(app, "dev")
    config_id = dev.post("/configs", _make_payload()).json()["id"]

    root = authenticated_client(app, "root")
    detail = root.get(f"/configs/{config_id}").json()
    assert detail["access"] == "owner"
    assert root.delete(f"/configs/{config_id}").status_code == 204
