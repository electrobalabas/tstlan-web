from dataclasses import dataclass
from typing import Self

from tstlan.devices.models import Device, DeviceStatus
from tstlan.devices.simulation.signals import Signal
from tstlan.models import NetVar, NetVarCType, NetVarMode


@dataclass
class SimulatedDevice:
    """Тестовый прибор."""

    device: Device
    signals: dict[str, Signal]
    handle: int = 0


class SimulatedDeviceBuilder:
    def __init__(
        self, device_id: str, name: str, *, type: str = "Эмулятор", enabled: bool = True
    ) -> None:
        self._id = device_id
        self._name = name
        self._type = type
        self._enabled = enabled
        self._variables: list[NetVar] = []
        self._signals: dict[str, Signal] = {}

    def sensor(self, name: str, ctype: NetVarCType, signal: Signal) -> Self:
        self._add(NetVar(name, ctype, NetVarMode.R))
        self._signals[name] = signal
        return self

    def control(
        self, name: str, ctype: NetVarCType, *, initial: int | float = 0
    ) -> Self:
        self._add(NetVar(name, ctype, NetVarMode.RW, value=initial))
        return self

    def command(self, name: str, ctype: NetVarCType) -> Self:
        self._add(NetVar(name, ctype, NetVarMode.W))
        return self

    def var(self, name: str) -> NetVar:
        for variable in self._variables:
            if variable.name == name:
                return variable
        raise KeyError(name)

    def build(self) -> SimulatedDevice:
        status = DeviceStatus.OK if self._enabled else DeviceStatus.OFFLINE
        device = Device(
            id=self._id,
            name=self._name,
            type=self._type,
            enabled=self._enabled,
            status=status,
            variables=self._variables,
        )
        return SimulatedDevice(device, self._signals)

    def _add(self, variable: NetVar) -> None:
        self._variables.append(variable)
