import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.devices.routes import stream_values, value_event_stream
from tstlan.devices.service import DeviceService


@pytest.mark.anyio
async def test_stream_emits_values_snapshot(devices_service: DeviceService) -> None:
    stream = value_event_stream(devices_service, "dev", asyncio.Event())
    event = await anext(stream)
    await stream.aclose()
    assert event.startswith("data: ")
    payload = json.loads(event.removeprefix("data: "))
    assert payload["t"] > 0  # серверное время unix в секундах
    assert any(item["name"] == "voltage" for item in payload["values"])


@pytest.mark.anyio
async def test_stream_stops_after_signal(devices_service: DeviceService) -> None:
    stop = asyncio.Event()
    stream = value_event_stream(devices_service, "dev", stop, interval=0.01)
    await anext(stream)
    stop.set()
    assert [event async for event in stream] == []


@pytest.mark.anyio
async def test_stream_yields_nothing_when_already_stopped(
    devices_service: DeviceService,
) -> None:
    stop = asyncio.Event()
    stop.set()
    stream = value_event_stream(devices_service, "dev", stop)
    assert [event async for event in stream] == []


def test_stream_uses_event_stream_media_type(devices_service: DeviceService) -> None:
    response = stream_values("dev", devices_service, asyncio.Event())
    assert response.media_type == "text/event-stream"


def test_stream_disables_proxy_transform(devices_service: DeviceService) -> None:
    # no-transform не даёт прокси сжимать/буферизовать поток (иначе EventSource молчит)
    response = stream_values("dev", devices_service, asyncio.Event())
    assert "no-transform" in response.headers["cache-control"]


def test_stream_unknown_device_returns_404(devices_client: TestClient) -> None:
    assert devices_client.get("/devices/ghost/stream").status_code == 404


def test_lifespan_signals_shutdown_to_streams() -> None:
    app = create_app()
    assert not app.state.shutdown_event.is_set()
    with TestClient(app):
        pass
    assert app.state.shutdown_event.is_set()
