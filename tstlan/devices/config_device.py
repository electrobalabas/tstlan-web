"""Построение прибора из конфига: `ConfigPayload` → доменный `Device`.

Конфиг (PR #35) описывает подключение и упорядоченный список переменных
(`ConfigVar`: имя, тип, graph, category) — но не режим доступа. Для тестового
прибора режим по умолчанию `RW`: значения и пишутся бэкендом, и читаются обратно.
Раскладку (offset) по-прежнему выводит `variable_offsets` из порядка и типа.
"""

from tstlan.configs.schemas import ConfigPayload
from tstlan.devices.models import Device, DeviceStatus
from tstlan.models import NetVar, NetVarMode


def variables_from_config(
    payload: ConfigPayload, *, mode: NetVarMode = NetVarMode.RW
) -> list[NetVar]:
    return [NetVar(var.name, var.ctype, mode) for var in payload.variables]


def device_from_config(
    device_id: str,
    name: str,
    payload: ConfigPayload,
    *,
    device_type: str = "Эмулятор",
    mode: NetVarMode = NetVarMode.RW,
    enabled: bool = True,
) -> Device:
    status = DeviceStatus.OK if enabled else DeviceStatus.OFFLINE
    return Device(
        id=device_id,
        name=name,
        type=device_type,
        enabled=enabled,
        status=status,
        variables=variables_from_config(payload, mode=mode),
    )
