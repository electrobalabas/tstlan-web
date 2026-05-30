import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from tstlan.devices.models import ValueValidationError
from tstlan.devices.schemas import (
    DeviceDetail,
    DeviceSummary,
    VariableValue,
    WriteValueRequest,
)
from tstlan.devices.service import (
    DeviceNotFound,
    DeviceService,
    VariableAccessError,
    VariableNotFound,
)

router = APIRouter(tags=["devices"])

_STREAM_INTERVAL_SECONDS = 1.0


def get_service(request: Request) -> DeviceService:
    return request.app.state.devices


Service = Annotated[DeviceService, Depends(get_service)]


@router.get("/devices")
def list_devices(service: Service) -> list[DeviceSummary]:
    return [DeviceSummary.from_device(device) for device in service.list_devices()]


@router.get("/devices/{device_id}")
def get_device(device_id: str, service: Service) -> DeviceDetail:
    return DeviceDetail.from_device(service.get_device(device_id))


@router.get("/devices/{device_id}/values")
def read_values(device_id: str, service: Service) -> list[VariableValue]:
    return [VariableValue.from_var(var) for var in service.read_values(device_id)]


@router.get("/devices/{device_id}/values/{name}")
def read_value(device_id: str, name: str, service: Service) -> VariableValue:
    return VariableValue.from_var(service.read_value(device_id, name))


@router.put("/devices/{device_id}/values/{name}")
def write_value(
    device_id: str, name: str, payload: WriteValueRequest, service: Service
) -> VariableValue:
    return VariableValue.from_var(service.write_value(device_id, name, payload.value))


async def value_event_stream(
    service: DeviceService,
    device_id: str,
    *,
    interval: float = _STREAM_INTERVAL_SECONDS,
) -> AsyncGenerator[str, None]:
    while True:
        snapshot = [
            VariableValue.from_var(var).model_dump(mode="json")
            for var in service.read_values(device_id)
        ]
        yield f"data: {json.dumps(snapshot)}\n\n"
        await asyncio.sleep(interval)


@router.get("/devices/{device_id}/stream")
def stream_values(device_id: str, service: Service) -> StreamingResponse:
    service.get_device(device_id)
    return StreamingResponse(
        value_event_stream(service, device_id), media_type="text/event-stream"
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DeviceNotFound, _not_found)
    app.add_exception_handler(VariableNotFound, _not_found)
    app.add_exception_handler(VariableAccessError, _forbidden)
    app.add_exception_handler(ValueValidationError, _unprocessable)


def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=404)


def _forbidden(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=403)


def _unprocessable(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=422)
