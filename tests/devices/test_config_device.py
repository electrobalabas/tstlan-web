import struct

from tstlan.configs.schemas import ConfigPayload, ConfigVar
from tstlan.devices.config_device import device_from_config
from tstlan.devices.runtime import bind_device
from tstlan.devices.service import DeviceService
from tstlan.devices.unidriver import InMemoryUnidriverIO
from tstlan.models import NetVarCType, NetVarMode
from tstlan.tools.ini2yaml import convert


def _payload() -> ConfigPayload:
    return ConfigPayload(
        variables=[
            ConfigVar(name="flag", ctype=NetVarCType.BIT),
            ConfigVar(name="count", ctype=NetVarCType.U32),
            ConfigVar(name="level", ctype=NetVarCType.F32),
        ]
    )


def test_device_from_config_maps_variables() -> None:
    device = device_from_config("m1", "Прибор", _payload())
    assert device.id == "m1"
    assert [(v.name, v.ctype, v.mode) for v in device.variables] == [
        ("flag", NetVarCType.BIT, NetVarMode.RW),
        ("count", NetVarCType.U32, NetVarMode.RW),
        ("level", NetVarCType.F32, NetVarMode.RW),
    ]


def test_config_layout_round_trips_through_seam() -> None:
    io = InMemoryUnidriverIO()
    runtime = bind_device(io, device_from_config("m1", "Прибор", _payload()), 1)
    runtime.scheme["count"].set(7)
    runtime.scheme["level"].set(2.5)
    runtime.scheme["flag"].set(1)
    # bit в байте 0, u32 со следующего байта, f32 после него.
    assert io.read_bytes(1, 1, 4) == struct.pack("<I", 7)
    assert io.read_bytes(1, 5, 4) == struct.pack("<f", 2.5)
    assert runtime.scheme["count"].get() == 7


def test_service_serves_a_config_device() -> None:
    device = device_from_config("m1", "Прибор", _payload())
    service = DeviceService.from_devices([device])
    service.write_value("m1", "count", 42)
    assert service.read_value("m1", "count").value == 42
    assert {var.name for var in service.read_values("m1")} == {"flag", "count", "level"}


def test_device_built_from_ini_config() -> None:
    ini = (
        "[device]\ntype=modbus udp\n\n"
        "[vars]\n"
        "Name_0=flag\nType_0=bit\nName_1=count\nType_1=u32\n"
    )
    payload = ConfigPayload.model_validate(convert(ini, "dev")["payload"])
    device = device_from_config("dev", "dev", payload)
    assert [v.name for v in device.variables] == ["flag", "count"]
