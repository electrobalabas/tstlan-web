import asyncio

import pytest

from tstlan.devices.simulation.builder import SimulatedDevice, SimulatedDeviceBuilder
from tstlan.devices.simulation.engine import SimulationEngine
from tstlan.devices.simulation.signals import Constant, Follow, Ramp
from tstlan.devices.unidriver import InMemoryUnidriverIO, build_scheme
from tstlan.models import NetVarCType


def _value(simulated: SimulatedDevice, name: str) -> int | float:
    return next(var for var in simulated.device.variables if var.name == name).value


def test_tick_advances_sensor_via_signal() -> None:
    simulated = (
        SimulatedDeviceBuilder("dev", "Прибор")
        .sensor("samples", NetVarCType.U32, Ramp(rate=1.0))
        .build()
    )
    SimulationEngine(InMemoryUnidriverIO(), [simulated]).tick(4.0)
    assert _value(simulated, "samples") == 4


def test_tick_leaves_controls_untouched() -> None:
    simulated = (
        SimulatedDeviceBuilder("dev", "Прибор")
        .control("range", NetVarCType.U8, initial=2)
        .build()
    )
    SimulationEngine(InMemoryUnidriverIO(), [simulated]).tick(10.0)
    assert _value(simulated, "range") == 2


def test_tick_skips_disabled_devices() -> None:
    simulated = (
        SimulatedDeviceBuilder("dev", "Прибор", enabled=False)
        .sensor("samples", NetVarCType.U32, Ramp(rate=1.0))
        .build()
    )
    SimulationEngine(InMemoryUnidriverIO(), [simulated]).tick(5.0)
    assert _value(simulated, "samples") == 0


def test_tick_clamps_and_rounds_to_register_type() -> None:
    simulated = (
        SimulatedDeviceBuilder("dev", "Прибор")
        .sensor("over", NetVarCType.U8, Constant(300.0))
        .sensor("frac", NetVarCType.U8, Constant(2.6))
        .build()
    )
    SimulationEngine(InMemoryUnidriverIO(), [simulated]).tick(0.0)
    assert _value(simulated, "over") == 255
    assert _value(simulated, "frac") == 3


def test_tick_lets_sensor_follow_a_control() -> None:
    builder = SimulatedDeviceBuilder("dev", "Прибор")
    builder.control("setpoint", NetVarCType.F32, initial=10.0)
    builder.sensor("output", NetVarCType.F32, Follow(builder.var("setpoint")))
    simulated = builder.build()

    io = InMemoryUnidriverIO()
    engine = SimulationEngine(io, [simulated])
    engine.tick(0.0)
    assert _value(simulated, "output") == 10.0

    # бэкенд пишет управляющую переменную через шов, а не в NetVar.value
    build_scheme(io, simulated.handle, [builder.var("setpoint")])[0].set(20.0)
    engine.tick(1.0)
    assert _value(simulated, "output") == 20.0


@pytest.mark.anyio
async def test_run_ticks_until_stopped() -> None:
    simulated = (
        SimulatedDeviceBuilder("dev", "Прибор")
        .sensor("samples", NetVarCType.U32, Ramp(rate=1000.0))
        .build()
    )
    engine = SimulationEngine(InMemoryUnidriverIO(), [simulated], interval=0.001)
    stop = asyncio.Event()

    task = asyncio.create_task(engine.run(stop))
    await asyncio.sleep(0.02)
    stop.set()
    await task

    assert _value(simulated, "samples") > 0


def test_engine_rejects_duplicate_handles() -> None:
    a = SimulatedDeviceBuilder("a", "A").sensor("x", NetVarCType.U8, Ramp(1.0)).build()
    b = SimulatedDeviceBuilder("b", "B").sensor("y", NetVarCType.U8, Ramp(1.0)).build()
    # оба прибора с handle=0 по умолчанию — схемы перетёрли бы друг друга
    with pytest.raises(ValueError):
        SimulationEngine(InMemoryUnidriverIO(), [a, b])
