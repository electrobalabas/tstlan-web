from pathlib import Path

from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.config import DeviceEndpoint, Settings

_SCENARIO = """
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


def test_simulation_engine_drives_served_values() -> None:
    app = create_app()
    client = TestClient(app)
    endpoint = "/devices/multimeter/values/samples"
    assert client.get(endpoint).json()["value"] == 0
    app.state.simulation.tick(5.0)
    assert client.get(endpoint).json()["value"] == 5


def test_external_devices_serve_metadata_without_emulator(tmp_path: Path) -> None:
    scenario = tmp_path / "mm.yaml"
    scenario.write_text(_SCENARIO, encoding="utf-8")
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        devices=[DeviceEndpoint(id="mm", port=1, scenario=scenario)],
    )
    app = create_app(settings=settings)
    # метаданные приборов не трогают сокет -> доступны до подъёма эмулятора
    assert app.state.simulation is None
    client = TestClient(app)
    assert {device["id"] for device in client.get("/devices").json()} == {"mm"}
    detail = client.get("/devices/mm").json()
    assert [var["name"] for var in detail["variables"]] == ["voltage", "range"]
