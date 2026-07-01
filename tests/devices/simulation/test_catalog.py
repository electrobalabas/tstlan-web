from tstlan.devices.simulation.builder import SimulatedDevice
from tstlan.devices.simulation.catalog import default_simulated_devices
from tstlan.devices.simulation.engine import SimulationEngine
from tstlan.devices.unidriver import InMemoryUnidriverIO
from tstlan.models import NetVarMode


def _by_id() -> dict[str, SimulatedDevice]:
    return {item.device.id: item for item in default_simulated_devices()}


def test_catalog_lists_expected_devices() -> None:
    assert set(_by_id()) == {"multimeter", "calibrator", "thermostat"}


def test_catalog_devices_are_enabled() -> None:
    assert all(item.device.enabled for item in default_simulated_devices())


def test_sensors_are_read_only() -> None:
    multimeter = _by_id()["multimeter"]
    voltage = next(v for v in multimeter.device.variables if v.name == "voltage")
    assert voltage.mode is NetVarMode.R


def test_calibrator_output_follows_setpoint() -> None:
    catalog = default_simulated_devices()
    calibrator = next(item for item in catalog if item.device.id == "calibrator")
    setpoint = next(v for v in calibrator.device.variables if v.name == "setpoint")
    output = next(v for v in calibrator.device.variables if v.name == "output")

    setpoint.value = 33.0
    SimulationEngine(InMemoryUnidriverIO(), catalog).tick(0.0)
    assert abs(output.value - 33.0) < 0.5
