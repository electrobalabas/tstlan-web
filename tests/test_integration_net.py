import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from devsim.server import HANDLE
from tstlan.app import create_app
from tstlan.config import DeviceEndpoint, Settings
from tstlan.devices.net.client import SocketUnidriverIO
from tstlan.devices.runtime import attach_device
from tstlan.devices.scenario import device_from_scenario, load_scenario
from tstlan.devices.service import DeviceService

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent / "fixtures" / "scenario.yaml"
REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def device_port() -> Iterator[int]:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "devsim",
            "--scenario",
            str(FIXTURE),
            "--port",
            "0",
        ],
        stdout=subprocess.PIPE,
        text=True,
        cwd=REPO_ROOT,
    )
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("процесс-прибор не стартовал")
        yield int(line.strip().rsplit(":", 1)[-1])
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def _service(port: int) -> DeviceService:
    io = SocketUnidriverIO("127.0.0.1", port)
    device = device_from_scenario(load_scenario(FIXTURE), "sim")
    return DeviceService([attach_device(io, device, HANDLE)])


def test_write_then_read_over_socket(device_port: int) -> None:
    service = _service(device_port)
    service.write_value("sim", "count", 123456)
    assert service.read_value("sim", "count").value == 123456


def test_bit_round_trip_over_socket(device_port: int) -> None:
    service = _service(device_port)
    service.write_value("sim", "flag", 1)
    assert service.read_value("sim", "flag").value == 1


def test_float_value_over_socket(device_port: int) -> None:
    service = _service(device_port)
    service.write_value("sim", "level", 2.5)
    assert service.read_value("sim", "level").value == 2.5


def test_simulated_sensor_over_socket(device_port: int) -> None:
    service = _service(device_port)
    assert service.read_value("sim", "meter").value == 99


def test_values_snapshot_over_socket(device_port: int) -> None:
    service = _service(device_port)
    assert {var.name for var in service.read_values("sim")} == {
        "flag",
        "count",
        "level",
        "meter",
    }


def test_app_reads_and_writes_device_over_socket(device_port: int) -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        devices=[DeviceEndpoint(id="sim", port=device_port, scenario=FIXTURE)],
    )
    client = TestClient(create_app(settings=settings))
    assert client.get("/devices/sim/values/meter").json()["value"] == 99
    client.put("/devices/sim/values/count", json={"value": 123})
    assert client.get("/devices/sim/values/count").json()["value"] == 123
