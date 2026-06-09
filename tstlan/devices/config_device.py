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
