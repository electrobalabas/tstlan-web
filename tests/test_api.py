from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.config import DeviceEndpoint, Settings

LoginAs = Callable[[FastAPI, Role], None]

_PROFILE = """
name: Мультиметр
device_type: multimeter
variables:
  - name: voltage
    ctype: f32
    signal: {kind: sine, amplitude: 0.5, period: 12.0, offset: 220.0}
  - name: range
    ctype: u8
    initial: 1
"""


def test_health_reports_ok() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_app_boots_with_db_lifespan() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    with TestClient(create_app(settings=settings)) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_lifespan_collects_value_history() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    app = create_app(settings=settings)
    with TestClient(app):
        pass
    # сэмплер успевает снять хотя бы одну точку с каждого прибора каталога
    assert set(app.state.history) == {"multimeter", "calibrator", "thermostat"}
    points = app.state.history["multimeter"]
    assert points[-1].values.keys() >= {"voltage", "current", "range"}


def test_simulation_engine_drives_served_values(login_as: LoginAs) -> None:
    app = create_app()
    login_as(app, Role.USER)
    client = TestClient(app)
    endpoint = "/devices/multimeter/values/samples"
    assert client.get(endpoint).json()["value"] == 0
    app.state.simulation.tick(5.0)
    assert client.get(endpoint).json()["value"] == 5


def test_external_devices_serve_metadata_without_emulator(
    tmp_path: Path, login_as: LoginAs
) -> None:
    profile = tmp_path / "mm.yaml"
    profile.write_text(_PROFILE, encoding="utf-8")
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        devices=[DeviceEndpoint(id="mm", port=1, profile=profile)],
    )
    app = create_app(settings=settings)
    # метаданные приборов не трогают сокет -> доступны до подъёма эмулятора
    assert app.state.simulation is None
    login_as(app, Role.USER)
    client = TestClient(app)
    assert {device["id"] for device in client.get("/devices").json()} == {"mm"}
    detail = client.get("/devices/mm").json()
    assert [var["name"] for var in detail["variables"]] == ["voltage", "range"]
