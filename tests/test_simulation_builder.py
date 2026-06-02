import pytest

from tstlan.devices.models import DeviceStatus
from tstlan.devices.simulation.builder import SimulatedDeviceBuilder
from tstlan.devices.simulation.signals import Constant
from tstlan.models import NetVarCType, NetVarMode


def test_sensor_is_read_only_and_registers_signal() -> None:
    built = (
        SimulatedDeviceBuilder("dev", "Прибор")
        .sensor("voltage", NetVarCType.F32, Constant(1.0))
        .build()
    )
    variable = built.device.variables[0]
    assert variable.name == "voltage"
    assert variable.mode is NetVarMode.R
    assert "voltage" in built.signals


def test_control_is_read_write_with_initial_value() -> None:
    built = (
        SimulatedDeviceBuilder("dev", "Прибор")
        .control("range", NetVarCType.U8, initial=3)
        .build()
    )
    variable = built.device.variables[0]
    assert variable.mode is NetVarMode.RW
    assert variable.value == 3
    assert built.signals == {}


def test_command_is_write_only() -> None:
    built = (
        SimulatedDeviceBuilder("dev", "Прибор").command("reset", NetVarCType.U8).build()
    )
    assert built.device.variables[0].mode is NetVarMode.W


def test_enabled_device_is_ok_disabled_is_offline() -> None:
    enabled = SimulatedDeviceBuilder("a", "A").build()
    disabled = SimulatedDeviceBuilder("b", "B", enabled=False).build()
    assert enabled.device.status is DeviceStatus.OK
    assert enabled.device.enabled
    assert disabled.device.status is DeviceStatus.OFFLINE
    assert not disabled.device.enabled


def test_var_returns_added_register() -> None:
    builder = SimulatedDeviceBuilder("dev", "Прибор")
    builder.control("setpoint", NetVarCType.F32, initial=2.0)
    assert builder.var("setpoint").value == 2.0


def test_var_raises_for_unknown_register() -> None:
    with pytest.raises(KeyError):
        SimulatedDeviceBuilder("dev", "Прибор").var("ghost")
