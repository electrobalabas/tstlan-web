from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.config import Settings

LoginAs = Callable[[FastAPI, Role], None]


def test_default_catalog_is_served(login_as: LoginAs) -> None:
    app = create_app()
    login_as(app, Role.USER)
    response = TestClient(app).get("/devices")
    assert response.status_code == 200
    assert response.json()


@pytest.mark.parametrize(
    "path",
    [
        "/devices",
        "/devices/dev",
        "/devices/dev/values",
        "/devices/dev/values/level",
        "/devices/dev/history",
        "/devices/dev/stream",
    ],
)
def test_read_without_session_returns_401(path: str) -> None:
    assert TestClient(create_app()).get(path).status_code == 401


def test_write_without_session_returns_401() -> None:
    client = TestClient(create_app())
    response = client.put("/devices/dev/values/level", json={"value": 1})
    assert response.status_code == 401


def test_user_role_reads_but_cannot_write(
    devices_app: FastAPI, login_as: LoginAs
) -> None:
    login_as(devices_app, Role.USER)
    client = TestClient(devices_app)
    assert client.get("/devices/dev/values/level").status_code == 200
    response = client.put("/devices/dev/values/level", json={"value": 2})
    assert response.status_code == 403


@pytest.mark.parametrize("role", [Role.DEV, Role.ADMIN])
def test_dev_and_admin_roles_can_write(
    devices_app: FastAPI, login_as: LoginAs, role: Role
) -> None:
    login_as(devices_app, role)
    client = TestClient(devices_app)
    response = client.put("/devices/dev/values/level", json={"value": 3})
    assert response.status_code == 200
    assert response.json()["value"] == 3


def test_real_session_reads_and_writes_devices(
    sqlite_url, seed_users, allowed_origin: str
) -> None:
    # сквозной путь без подмены зависимостей: логин -> cookie -> csrf -> прибор
    url = sqlite_url("devices.db")
    seed_users(url, [("bob", Role.DEV)])
    settings = Settings(database_url=url, allowed_origins=[allowed_origin])
    with TestClient(create_app(settings=settings)) as client:
        login = client.post(
            "/auth/login",
            json={"login": "bob", "password": "pw"},
            headers={"Origin": allowed_origin},
        )
        csrf_token = login.json()["csrf_token"]
        assert client.get("/devices").status_code == 200
        response = client.put(
            "/devices/multimeter/values/range",
            json={"value": 2},
            headers={"Origin": allowed_origin, "X-CSRF-Token": csrf_token},
        )
        assert response.status_code == 200
        assert response.json()["value"] == 2


def test_list_devices_returns_summaries(devices_client: TestClient) -> None:
    response = devices_client.get("/devices")
    assert response.status_code == 200
    assert {device["id"] for device in response.json()} == {"dev", "spare"}


def test_get_device_returns_detail_with_variables(devices_client: TestClient) -> None:
    response = devices_client.get("/devices/dev")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "dev"
    assert any(var["name"] == "voltage" for var in body["variables"])


def test_get_unknown_device_returns_404(devices_client: TestClient) -> None:
    assert devices_client.get("/devices/ghost").status_code == 404


def test_read_values_excludes_write_only(devices_client: TestClient) -> None:
    response = devices_client.get("/devices/dev/values")
    assert response.status_code == 200
    assert "reset" not in {var["name"] for var in response.json()}


def test_read_single_value(devices_client: TestClient) -> None:
    response = devices_client.get("/devices/dev/values/level")
    assert response.status_code == 200
    assert response.json() == {"name": "level", "ctype": "u8", "value": 1}


def test_read_write_only_value_returns_403(devices_client: TestClient) -> None:
    assert devices_client.get("/devices/dev/values/reset").status_code == 403


def test_read_unknown_value_returns_404(devices_client: TestClient) -> None:
    assert devices_client.get("/devices/dev/values/ghost").status_code == 404


def test_write_value_echoes_new_value(devices_client: TestClient) -> None:
    response = devices_client.put("/devices/dev/values/level", json={"value": 5})
    assert response.status_code == 200
    assert response.json() == {"name": "level", "ctype": "u8", "value": 5}


def test_write_persists_for_next_read(devices_client: TestClient) -> None:
    devices_client.put("/devices/dev/values/level", json={"value": 9})
    assert devices_client.get("/devices/dev/values/level").json()["value"] == 9


def test_write_read_only_value_returns_403(devices_client: TestClient) -> None:
    response = devices_client.put("/devices/dev/values/counter", json={"value": 1})
    assert response.status_code == 403


def test_write_out_of_range_returns_422(devices_client: TestClient) -> None:
    response = devices_client.put("/devices/dev/values/level", json={"value": 999})
    assert response.status_code == 422


def test_write_rejects_non_numeric_value(devices_client: TestClient) -> None:
    response = devices_client.put("/devices/dev/values/level", json={"value": "x"})
    assert response.status_code == 422


def test_write_rejects_unknown_field(devices_client: TestClient) -> None:
    response = devices_client.put(
        "/devices/dev/values/level", json={"value": 1, "extra": 2}
    )
    assert response.status_code == 422


def test_write_requires_value_field(devices_client: TestClient) -> None:
    assert devices_client.put("/devices/dev/values/level", json={}).status_code == 422
