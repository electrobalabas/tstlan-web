from fastapi.testclient import TestClient

from tstlan.app import create_app


def client() -> TestClient:
    return TestClient(create_app())


def test_list_devices_returns_summaries() -> None:
    response = client().get("/devices")
    assert response.status_code == 200
    assert {device["id"] for device in response.json()} == {"multimeter", "calibrator"}


def test_get_device_returns_detail_with_variables() -> None:
    response = client().get("/devices/multimeter")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "multimeter"
    assert any(var["name"] == "voltage" for var in body["variables"])


def test_get_unknown_device_returns_404() -> None:
    assert client().get("/devices/ghost").status_code == 404


def test_read_values_excludes_write_only() -> None:
    response = client().get("/devices/multimeter/values")
    assert response.status_code == 200
    names = {var["name"] for var in response.json()}
    assert "reset" not in names


def test_read_single_value() -> None:
    response = client().get("/devices/multimeter/values/range")
    assert response.status_code == 200
    assert response.json() == {"name": "range", "ctype": "u8", "value": 1}


def test_read_write_only_value_returns_403() -> None:
    assert client().get("/devices/multimeter/values/reset").status_code == 403


def test_read_unknown_value_returns_404() -> None:
    assert client().get("/devices/multimeter/values/ghost").status_code == 404


def test_write_value_updates_and_echoes() -> None:
    response = client().put("/devices/multimeter/values/range", json={"value": 5})
    assert response.status_code == 200
    assert response.json() == {"name": "range", "ctype": "u8", "value": 5}


def test_write_read_only_value_returns_403() -> None:
    response = client().put("/devices/multimeter/values/counter", json={"value": 1})
    assert response.status_code == 403


def test_write_out_of_range_returns_422() -> None:
    response = client().put("/devices/multimeter/values/range", json={"value": 999})
    assert response.status_code == 422


def test_write_rejects_non_numeric_value() -> None:
    response = client().put("/devices/multimeter/values/range", json={"value": "x"})
    assert response.status_code == 422


def test_write_rejects_unknown_field() -> None:
    response = client().put(
        "/devices/multimeter/values/range", json={"value": 1, "extra": 2}
    )
    assert response.status_code == 422


def test_write_requires_value_field() -> None:
    assert client().put("/devices/multimeter/values/range", json={}).status_code == 422
