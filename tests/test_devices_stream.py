import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.devices.routes import stream_values, value_event_stream
from tstlan.devices.service import DeviceService, default_devices


@pytest.mark.anyio
async def test_stream_emits_values_snapshot() -> None:
    stop = asyncio.Event()
    stream = value_event_stream(DeviceService(default_devices()), "multimeter", stop)
    event = await anext(stream)
    await stream.aclose()
    assert event.startswith("data: ")
    payload = json.loads(event.removeprefix("data: "))
    assert any(item["name"] == "voltage" for item in payload)


@pytest.mark.anyio
async def test_stream_stops_after_signal() -> None:
    stop = asyncio.Event()
    stream = value_event_stream(
        DeviceService(default_devices()), "multimeter", stop, interval=0.01
    )
    await anext(stream)
    stop.set()
    assert [event async for event in stream] == []


@pytest.mark.anyio
async def test_stream_yields_nothing_when_already_stopped() -> None:
    stop = asyncio.Event()
    stop.set()
    stream = value_event_stream(DeviceService(default_devices()), "multimeter", stop)
    assert [event async for event in stream] == []


def test_stream_uses_event_stream_media_type() -> None:
    response = stream_values(
        "multimeter", DeviceService(default_devices()), asyncio.Event()
    )
    assert response.media_type == "text/event-stream"


def test_stream_unknown_device_returns_404() -> None:
    assert TestClient(create_app()).get("/devices/ghost/stream").status_code == 404


def test_lifespan_signals_shutdown_to_streams() -> None:
    app = create_app()
    assert not app.state.shutdown_event.is_set()
    with TestClient(app):
        pass
    assert app.state.shutdown_event.is_set()
