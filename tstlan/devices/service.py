import logging
from collections.abc import Sequence

from tstlan.devices.models import Device, coerce_value
from tstlan.devices.runtime import DeviceRuntime, bind_device
from tstlan.devices.unidriver import InMemoryUnidriverIO, UnidriverIO
from tstlan.logging_setup import get_service_logger, log_event
from tstlan.models import NetVar, NetVarMode

logger = get_service_logger("devices")


class DeviceNotFound(Exception):
    pass


class VariableNotFound(Exception):
    pass


class VariableAccessError(Exception):
    pass


class DeviceService:
    """Доступ бэкенда к приборам: значения читаются/пишутся через шов."""

    def __init__(self, runtimes: Sequence[DeviceRuntime]) -> None:
        self._devices = {runtime.device.id: runtime for runtime in runtimes}
        log_event(
            logger, logging.INFO, "devices.service.created", count=len(self._devices)
        )

    @classmethod
    def from_devices(
        cls, devices: Sequence[Device], *, io: UnidriverIO | None = None
    ) -> "DeviceService":
        io = io or InMemoryUnidriverIO()
        return cls(
            [
                bind_device(io, device, handle)
                for handle, device in enumerate(devices, 1)
            ]
        )

    def list_devices(self) -> list[Device]:
        devices = [runtime.device for runtime in self._devices.values()]
        log_event(logger, logging.DEBUG, "devices.listed", count=len(devices))
        return devices

    def get_device(self, device_id: str) -> Device:
        return self._runtime(device_id).device

    def read_values(self, device_id: str) -> list[NetVar]:
        runtime = self._runtime(device_id)
        values = [
            self._snapshot(runtime, var)
            for var in runtime.device.variables
            if var.mode is not NetVarMode.W
        ]
        log_event(
            logger,
            logging.DEBUG,
            "devices.values.read",
            device_id=device_id,
            count=len(values),
        )
        return values

    def read_value(self, device_id: str, name: str) -> NetVar:
        runtime = self._runtime(device_id)
        var = self._variable(runtime, name)
        if var.mode is NetVarMode.W:
            log_event(
                logger,
                logging.WARNING,
                "devices.value.read_rejected",
                device_id=device_id,
                variable=name,
                reason="write_only",
            )
            raise VariableAccessError(name)
        value = self._snapshot(runtime, var)
        log_event(
            logger,
            logging.DEBUG,
            "devices.value.read",
            device_id=device_id,
            variable=name,
        )
        return value

    def write_value(self, device_id: str, name: str, value: int | float) -> NetVar:
        runtime = self._runtime(device_id)
        var = self._variable(runtime, name)
        if var.mode is NetVarMode.R:
            log_event(
                logger,
                logging.WARNING,
                "devices.value.write_rejected",
                device_id=device_id,
                variable=name,
                reason="read_only",
            )
            raise VariableAccessError(name)
        coerced = coerce_value(var.ctype, value)
        runtime.scheme[name].set(coerced)
        log_event(
            logger,
            logging.INFO,
            "devices.value.written",
            device_id=device_id,
            variable=name,
            ctype=var.ctype,
        )
        return NetVar(var.name, var.ctype, var.mode, value=coerced)

    def _snapshot(self, runtime: DeviceRuntime, var: NetVar) -> NetVar:
        value = runtime.scheme[var.name].get()
        return NetVar(var.name, var.ctype, var.mode, value=value)

    def _runtime(self, device_id: str) -> DeviceRuntime:
        try:
            return self._devices[device_id]
        except KeyError:
            log_event(logger, logging.WARNING, "devices.not_found", device_id=device_id)
            raise DeviceNotFound(device_id) from None

    def _variable(self, runtime: DeviceRuntime, name: str) -> NetVar:
        for var in runtime.device.variables:
            if var.name == name:
                return var
        log_event(
            logger,
            logging.WARNING,
            "devices.variable.not_found",
            device_id=runtime.device.id,
            variable=name,
        )
        raise VariableNotFound(name)
