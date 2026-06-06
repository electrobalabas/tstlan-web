"""Прибор глазами бэкенда: метаданные + аксессоры переменных через шов.

Значения переменных живут в байтовом буфере прибора за `UnidriverIO`, а не в
`NetVar.value`. `bind_device` строит аксессоры по раскладке из конфига и
публикует начальные значения в буфер.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from tstlan.devices.models import Device
from tstlan.devices.unidriver import NetVarAccessor, UnidriverIO, build_scheme
from tstlan.models import NetVar


@dataclass
class DeviceRuntime:
    device: Device
    scheme: dict[str, NetVarAccessor]


def publish_values(
    scheme: dict[str, NetVarAccessor], variables: Sequence[NetVar]
) -> None:
    """Записать текущие `NetVar.value` в буфер прибора (начальное состояние)."""
    for var in variables:
        scheme[var.name].set(var.value)


def bind_device(io: UnidriverIO, device: Device, handle: int) -> DeviceRuntime:
    scheme = {acc.name: acc for acc in build_scheme(io, handle, device.variables)}
    publish_values(scheme, device.variables)
    return DeviceRuntime(device, scheme)
