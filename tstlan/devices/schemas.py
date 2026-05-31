from pydantic import BaseModel, ConfigDict

from tstlan.devices.models import Device, DeviceStatus
from tstlan.models import NetVar, NetVarCType, NetVarMode


class VariableInfo(BaseModel):
    name: str
    ctype: NetVarCType
    mode: NetVarMode

    @classmethod
    def from_var(cls, var: NetVar) -> "VariableInfo":
        return cls(name=var.name, ctype=var.ctype, mode=var.mode)


class DeviceSummary(BaseModel):
    id: str
    name: str
    type: str
    enabled: bool
    status: DeviceStatus
    variable_count: int

    @classmethod
    def from_device(cls, device: Device) -> "DeviceSummary":
        return cls(
            id=device.id,
            name=device.name,
            type=device.type,
            enabled=device.enabled,
            status=device.status,
            variable_count=len(device.variables),
        )


class DeviceDetail(BaseModel):
    id: str
    name: str
    type: str
    enabled: bool
    status: DeviceStatus
    variables: list[VariableInfo]

    @classmethod
    def from_device(cls, device: Device) -> "DeviceDetail":
        return cls(
            id=device.id,
            name=device.name,
            type=device.type,
            enabled=device.enabled,
            status=device.status,
            variables=[VariableInfo.from_var(var) for var in device.variables],
        )


class VariableValue(BaseModel):
    name: str
    ctype: NetVarCType
    value: int | float

    @classmethod
    def from_var(cls, var: NetVar) -> "VariableValue":
        return cls(name=var.name, ctype=var.ctype, value=var.value)


class WriteValueRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    value: int | float
