import pytest

from tstlan.devices.models import Device, DeviceStatus, ValueValidationError
from tstlan.devices.service import (
    DeviceNotFound,
    DeviceService,
    VariableAccessError,
    VariableNotFound,
)
from tstlan.models import NetVar, NetVarCType, NetVarMode


def make_service() -> DeviceService:
    return DeviceService(
        [
            Device(
                id="dev",
                name="Устройство",
                type="Эмулятор",
                enabled=True,
                status=DeviceStatus.OK,
                variables=[
                    NetVar("ro", NetVarCType.U8, NetVarMode.R, value=7),
                    NetVar("rw", NetVarCType.U16, NetVarMode.RW, value=3),
                    NetVar("wo", NetVarCType.U8, NetVarMode.W),
                ],
            )
        ]
    )


def test_list_devices_returns_all_registered() -> None:
    service = DeviceService(
        [
            Device("a", "A", "Эмулятор", True, DeviceStatus.OK),
            Device("b", "B", "Эмулятор", False, DeviceStatus.OFFLINE),
        ]
    )
    assert [device.id for device in service.list_devices()] == ["a", "b"]


def test_get_device_returns_matching_device() -> None:
    assert make_service().get_device("dev").name == "Устройство"


def test_get_unknown_device_raises() -> None:
    with pytest.raises(DeviceNotFound):
        make_service().get_device("ghost")


def test_read_values_excludes_write_only() -> None:
    names = [var.name for var in make_service().read_values("dev")]
    assert names == ["ro", "rw"]


def test_read_value_returns_variable() -> None:
    assert make_service().read_value("dev", "ro").value == 7


def test_read_write_only_variable_raises() -> None:
    with pytest.raises(VariableAccessError):
        make_service().read_value("dev", "wo")


def test_read_unknown_variable_raises() -> None:
    with pytest.raises(VariableNotFound):
        make_service().read_value("dev", "ghost")


def test_write_value_updates_variable() -> None:
    assert make_service().write_value("dev", "rw", 42).value == 42


def test_write_read_only_variable_raises() -> None:
    with pytest.raises(VariableAccessError):
        make_service().write_value("dev", "ro", 1)


def test_write_out_of_range_raises() -> None:
    with pytest.raises(ValueValidationError):
        make_service().write_value("dev", "rw", 70000)


def test_write_unknown_variable_raises() -> None:
    with pytest.raises(VariableNotFound):
        make_service().write_value("dev", "ghost", 1)


def test_write_unknown_device_raises() -> None:
    with pytest.raises(DeviceNotFound):
        make_service().write_value("ghost", "rw", 1)
