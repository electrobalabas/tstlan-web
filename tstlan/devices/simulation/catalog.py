from tstlan.devices.simulation.builder import SimulatedDevice, SimulatedDeviceBuilder
from tstlan.devices.simulation.signals import (
    Follow,
    Noise,
    Ramp,
    RandomWalk,
    Sine,
    Square,
)
from tstlan.models import NetVarCType


def default_simulated_devices() -> list[SimulatedDevice]:
    devices = [_multimeter(), _calibrator(), _thermostat()]
    for handle, simulated in enumerate(devices, start=1):
        simulated.handle = handle
    return devices


def _multimeter() -> SimulatedDevice:
    builder = SimulatedDeviceBuilder("multimeter", "Тестовый мультиметр")
    builder.sensor(
        "voltage",
        NetVarCType.F32,
        Sine(amplitude=0.5, period=12.0, offset=220.0) + Noise(0.05, seed=1),
    )
    builder.sensor(
        "current",
        NetVarCType.F32,
        Sine(amplitude=0.2, period=7.0, offset=1.5, phase=1.0) + Noise(0.02, seed=2),
    )
    builder.sensor("samples", NetVarCType.U32, Ramp(rate=1.0))
    builder.control("range", NetVarCType.U8, initial=1)
    builder.command("reset", NetVarCType.U8)
    return builder.build()


def _calibrator() -> SimulatedDevice:
    builder = SimulatedDeviceBuilder("calibrator", "Калибратор")
    builder.control("setpoint", NetVarCType.F32, initial=10.0)
    builder.sensor(
        "output", NetVarCType.F32, Follow(builder.var("setpoint")) + Noise(0.01, seed=3)
    )
    builder.control("output_on", NetVarCType.U8, initial=1)
    builder.command("reset", NetVarCType.U8)
    return builder.build()


def _thermostat() -> SimulatedDevice:
    builder = SimulatedDeviceBuilder("thermostat", "Термостат")
    builder.sensor(
        "temperature",
        NetVarCType.F32,
        RandomWalk(start=25.0, step=0.1, low=20.0, high=30.0, seed=5),
    )
    builder.sensor("heater", NetVarCType.U8, Square(period=20.0, low=0.0, high=1.0))
    builder.control("setpoint", NetVarCType.F32, initial=25.0)
    return builder.build()
