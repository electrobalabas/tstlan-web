from pathlib import Path

from tstlan.devices.scenario import device_from_scenario, load_scenario
from tstlan.models import NetVarCType, NetVarMode

_YAML = """
name: Тестовый мультиметр
device_type: multimeter
variables:
  - name: voltage
    ctype: f32
    signal: {kind: sine, amplitude: 0.5, period: 12.0, offset: 220.0}
  - name: range
    ctype: u8
    initial: 1
  - name: reset
    ctype: u8
    mode: w
"""


def _scenario(tmp_path: Path):
    path = tmp_path / "device.yaml"
    path.write_text(_YAML, encoding="utf-8")
    return load_scenario(path)


def test_scenario_resolves_variable_modes(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path)
    assert [(v.name, v.ctype, v.mode, v.value) for v in scenario.variables] == [
        ("voltage", NetVarCType.F32, NetVarMode.R, 0),
        ("range", NetVarCType.U8, NetVarMode.RW, 1),
        ("reset", NetVarCType.U8, NetVarMode.W, 0),
    ]


def test_scenario_collects_signal_specs(tmp_path: Path) -> None:
    scenario = _scenario(tmp_path)
    assert scenario.signals == {
        "voltage": {"kind": "sine", "amplitude": 0.5, "period": 12.0, "offset": 220.0}
    }


def test_device_from_scenario_carries_metadata(tmp_path: Path) -> None:
    device = device_from_scenario(_scenario(tmp_path), "mm1")
    assert (device.id, device.name, device.type) == (
        "mm1",
        "Тестовый мультиметр",
        "multimeter",
    )
    assert [v.name for v in device.variables] == ["voltage", "range", "reset"]
