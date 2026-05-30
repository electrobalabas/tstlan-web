import json

import pytest
from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.devices.routes import stream_values, value_event_stream
from tstlan.devices.service import DeviceService, default_devices


@pytest.mark.anyio
async def test_value_event_stream_emits_values_snapshot() -> None:
    stream = value_event_stream(DeviceService(default_devices()), "multimeter")
    event = await anext(stream)
    await stream.aclose()
    assert event.startswith("data: ")
    payload = json.loads(event.removeprefix("data: "))
    assert any(item["name"] == "voltage" for item in payload)


def test_stream_uses_event_stream_media_type() -> None:
    response = stream_values("multimeter", DeviceService(default_devices()))
    assert response.media_type == "text/event-stream"


def test_stream_unknown_device_returns_404() -> None:
    assert TestClient(create_app()).get("/devices/ghost/stream").status_code == 404
