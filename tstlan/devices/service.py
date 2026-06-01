from tstlan.devices.models import Device, coerce_value
from tstlan.models import NetVar, NetVarMode


class DeviceNotFound(Exception):
    pass


class VariableNotFound(Exception):
    pass


class VariableAccessError(Exception):
    pass


class DeviceService:
    def __init__(self, devices: list[Device]) -> None:
        self._devices = {device.id: device for device in devices}

    def list_devices(self) -> list[Device]:
        return list(self._devices.values())

    def get_device(self, device_id: str) -> Device:
        try:
            return self._devices[device_id]
        except KeyError:
            raise DeviceNotFound(device_id) from None

    def read_values(self, device_id: str) -> list[NetVar]:
        device = self.get_device(device_id)
        return [var for var in device.variables if var.mode is not NetVarMode.W]

    def read_value(self, device_id: str, name: str) -> NetVar:
        var = self._get_variable(device_id, name)
        if var.mode is NetVarMode.W:
            raise VariableAccessError(name)
        return var

    def write_value(self, device_id: str, name: str, value: int | float) -> NetVar:
        var = self._get_variable(device_id, name)
        if var.mode is NetVarMode.R:
            raise VariableAccessError(name)
        var.value = coerce_value(var.ctype, value)
        return var

    def _get_variable(self, device_id: str, name: str) -> NetVar:
        device = self.get_device(device_id)
        for var in device.variables:
            if var.name == name:
                return var
        raise VariableNotFound(name)
