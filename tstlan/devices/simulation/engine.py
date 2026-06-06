import asyncio
import time
from collections.abc import Callable, Iterable

from tstlan.devices.models import fit_value
from tstlan.devices.runtime import publish_values
from tstlan.devices.simulation.builder import SimulatedDevice
from tstlan.devices.unidriver import NetVarAccessor, UnidriverIO, build_scheme
from tstlan.models import NetVarMode

DEFAULT_INTERVAL_SECONDS = 0.5


class SimulationEngine:
    """Сторона прибора: генерирует значения сенсоров в буфер за швом.

    На каждый тик считывает управляющие переменные из буфера (их пишет бэкенд),
    вычисляет сигналы сенсоров и публикует их обратно в буфер.
    """

    def __init__(
        self,
        io: UnidriverIO,
        devices: Iterable[SimulatedDevice],
        *,
        interval: float = DEFAULT_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._io = io
        self._devices = list(devices)
        self._interval = interval
        self._clock = clock
        self._schemes: dict[int, dict[str, NetVarAccessor]] = {}
        for simulated in self._devices:
            if simulated.handle in self._schemes:
                raise ValueError(f"дублирующийся handle прибора: {simulated.handle}")
            scheme = {
                acc.name: acc
                for acc in build_scheme(
                    io, simulated.handle, simulated.device.variables
                )
            }
            self._schemes[simulated.handle] = scheme
            publish_values(scheme, simulated.device.variables)

    def tick(self, t: float) -> None:
        for simulated in self._devices:
            if not simulated.device.enabled:
                continue
            scheme = self._schemes[simulated.handle]
            for variable in simulated.device.variables:
                if variable.mode is not NetVarMode.R:
                    variable.value = scheme[variable.name].get()
            for variable in simulated.device.variables:
                signal = simulated.signals.get(variable.name)
                if signal is None:
                    continue
                variable.value = fit_value(variable.ctype, signal.sample(t))
                scheme[variable.name].set(variable.value)

    async def run(self, stop: asyncio.Event) -> None:
        start = self._clock()
        while not stop.is_set():
            self.tick(self._clock() - start)
            await self._wait(stop)

    async def _wait(self, stop: asyncio.Event) -> None:
        try:
            await asyncio.wait_for(stop.wait(), timeout=self._interval)
        except TimeoutError:
            pass
