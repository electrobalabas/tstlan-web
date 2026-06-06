"""Интеграция: прибор как отдельный процесс, бэкенд по реальному TCP-сокету.

Раскладка переменных у прибора и у бэкенда выводится из одного YAML-конфига.
Маркер `integration` — запуск только локально (`pytest -m integration`), не в CI.
"""

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from tstlan.devices.config_device import device_from_config
from tstlan.devices.net.client import SocketUnidriverIO
from tstlan.devices.net.server import HANDLE, load_payload
from tstlan.devices.runtime import attach_device
from tstlan.devices.service import DeviceService

pytestmark = pytest.mark.integration

FIXTURE = Path(__file__).parent / "fixtures" / "device.yaml"
REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def device_port() -> Iterator[int]:
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "tstlan.devices.net.server",
            "--config",
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
    device = device_from_config("sim", "Прибор", load_payload(FIXTURE))
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


def test_values_snapshot_over_socket(device_port: int) -> None:
    service = _service(device_port)
    assert {var.name for var in service.read_values("sim")} == {
        "flag",
        "count",
        "level",
    }
