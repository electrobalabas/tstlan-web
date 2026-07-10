import os
import socket
import subprocess
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.config import DeviceEndpoint, Settings
from tstlan.devices.device_profile import device_from_profile, load_profile
from tstlan.devices.net.client import SocketUnidriverIO
from tstlan.devices.runtime import attach_device
from tstlan.devices.service import DeviceService

pytestmark = pytest.mark.docker_integration

FIXTURE = Path(__file__).parents[1] / "fixtures" / "device_profile.yaml"
REPO_ROOT = Path(__file__).parents[2]
IMAGE = "tstlan-native-unidriver-fixture:pytest"
HANDLE = 1


@pytest.fixture(scope="session")
def docker_image() -> str:
    if not _docker_available():
        if os.environ.get("CI") == "true":
            pytest.fail("Docker is required in CI for native unidriver tests")
        pytest.skip("Docker is required for native unidriver integration tests")
    _docker_build(
        [
            "docker",
            "build",
            "--progress",
            "plain",
            "-t",
            IMAGE,
            "-f",
            "tests/docker/unidriver/Dockerfile",
            ".",
        ],
    )
    return IMAGE


@pytest.fixture
def device_port(docker_image: str) -> Iterator[int]:
    proc = subprocess.run(
        ["docker", "run", "--rm", "-d", "-p", "127.0.0.1::9000", docker_image],
        check=True,
        capture_output=True,
        text=True,
    )
    container_id = proc.stdout.strip()
    try:
        port = _published_port(container_id)
        _wait_for_port(port)
        yield port
    finally:
        subprocess.run(["docker", "rm", "-f", container_id], check=False)


def _service(port: int) -> DeviceService:
    io = SocketUnidriverIO("127.0.0.1", port)
    device = device_from_profile(load_profile(FIXTURE), "native")
    return DeviceService([attach_device(io, device, HANDLE)])


def test_docker_native_unidriver_round_trip(device_port: int) -> None:
    service = _service(device_port)

    service.write_value("native", "flag", 1)
    service.write_value("native", "count", 123456)
    service.write_value("native", "level", 2.5)

    assert service.read_value("native", "flag").value == 1
    assert service.read_value("native", "count").value == 123456
    assert service.read_value("native", "level").value == 2.5


def test_app_reads_and_writes_docker_native_unidriver(
    device_port: int, login_as: Callable[[FastAPI, Role], None]
) -> None:
    settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        devices=[DeviceEndpoint(id="native", port=device_port, profile=FIXTURE)],
    )
    app = create_app(settings=settings)
    login_as(app, Role.DEV)
    client = TestClient(app)

    client.put("/devices/native/values/count", json={"value": 777})

    assert client.get("/devices/native/values/count").json()["value"] == 777


def _docker_available() -> bool:
    try:
        subprocess.run(
            ["docker", "version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired:
        return False
    return True


def _docker_build(command: list[str]) -> None:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"docker build failed\n\nstdout:\n{proc.stdout}\n\nstderr:\n{proc.stderr}"
        )


def _published_port(container_id: str) -> int:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        proc = subprocess.run(
            ["docker", "port", container_id, "9000/tcp"],
            check=True,
            capture_output=True,
            text=True,
        )
        line = proc.stdout.strip().splitlines()
        if line:
            return int(line[0].rsplit(":", 1)[-1])
        time.sleep(0.1)
    raise RuntimeError(f"container {container_id} did not publish port 9000")


def _wait_for_port(port: int) -> None:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"Docker native unidriver did not listen on {port}")
