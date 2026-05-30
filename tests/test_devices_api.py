from fastapi.testclient import TestClient

from tstlan.app import create_app


def test_default_catalog_is_served() -> None:
    response = TestClient(create_app()).get("/devices")
    assert response.status_code == 200
    assert response.json()


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
