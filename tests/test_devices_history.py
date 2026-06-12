import asyncio
from itertools import count
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tstlan.devices.history import (
    MAX_POINTS,
    device_history,
    new_history,
    record_snapshot,
    run_sampler,
)
from tstlan.devices.service import DeviceService
from tstlan.models import NetVar


def _clock() -> "count[int]":
    return count(start=100)


def test_snapshot_records_readable_values(devices_service: DeviceService) -> None:
    history = new_history()
    ticks = _clock()
    record_snapshot(history, devices_service, clock=lambda: next(ticks))
    points = device_history(history, "dev")
    assert len(points) == 1
    assert points[0].t == 100
    assert points[0].values["level"] == 1
    # write-only переменные не читаются и в историю не попадают
    assert "reset" not in points[0].values


def test_snapshot_covers_every_device(devices_service: DeviceService) -> None:
    history = new_history()
    record_snapshot(history, devices_service)
    assert set(history) == {"dev", "spare"}


def test_history_window_is_bounded(devices_service: DeviceService) -> None:
    history = new_history()
    for _ in range(MAX_POINTS + 10):
        record_snapshot(history, devices_service)
    points = device_history(history, "dev")
    assert len(points) == MAX_POINTS


def test_oldest_points_are_evicted_first(devices_service: DeviceService) -> None:
    history = new_history()
    ticks = _clock()
    for _ in range(MAX_POINTS + 5):
        record_snapshot(history, devices_service, clock=lambda: next(ticks))
    points = device_history(history, "dev")
    assert points[0].t == 100 + 5 * 2  # по тику на каждый из двух приборов
    assert points[-1].t > points[0].t


def test_unknown_device_history_is_empty(devices_service: DeviceService) -> None:
    assert device_history(new_history(), "ghost") == []


def test_unreachable_device_is_skipped(devices_service: DeviceService) -> None:
    real_read = devices_service.read_values

    def flaky(device_id: str) -> list[NetVar]:
        if device_id == "dev":
            raise ConnectionError("прибор недоступен")
        return real_read(device_id)

    history = new_history()
    with patch.object(devices_service, "read_values", flaky):
        record_snapshot(history, devices_service)
    assert device_history(history, "dev") == []
    assert len(device_history(history, "spare")) == 1


@pytest.mark.anyio
async def test_sampler_records_and_stops(devices_service: DeviceService) -> None:
    history = new_history()
    stop = asyncio.Event()
    task = asyncio.create_task(run_sampler(history, devices_service, stop, interval=60))
    await asyncio.sleep(0)  # первая точка пишется до первого ожидания
    assert len(device_history(history, "dev")) == 1
    stop.set()
    await task


@pytest.mark.anyio
async def test_sampler_with_stop_set_records_nothing(
    devices_service: DeviceService,
) -> None:
    history = new_history()
    stop = asyncio.Event()
    stop.set()
    await run_sampler(history, devices_service, stop)
    assert history == new_history()


def test_history_endpoint_returns_recorded_points(
    devices_app: FastAPI,
    devices_service: DeviceService,
    devices_client: TestClient,
) -> None:
    record_snapshot(devices_app.state.history, devices_service, clock=lambda: 42.0)
    response = devices_client.get("/devices/dev/history")
    assert response.status_code == 200
    [point] = response.json()
    assert point["t"] == 42.0
    assert point["values"]["level"] == 1


def test_history_before_first_snapshot_is_empty(devices_client: TestClient) -> None:
    response = devices_client.get("/devices/dev/history")
    assert response.status_code == 200
    assert response.json() == []


def test_history_of_unknown_device_returns_404(devices_client: TestClient) -> None:
    assert devices_client.get("/devices/ghost/history").status_code == 404
