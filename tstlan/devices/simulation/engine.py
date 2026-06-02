import asyncio
import time
from collections.abc import Callable, Iterable

from tstlan.devices.models import fit_value
from tstlan.devices.simulation.builder import SimulatedDevice

DEFAULT_INTERVAL_SECONDS = 0.5


class SimulationEngine:
    def __init__(
        self,
        devices: Iterable[SimulatedDevice],
        *,
        interval: float = DEFAULT_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._devices = list(devices)
        self._interval = interval
        self._clock = clock

    def tick(self, t: float) -> None:
        for simulated in self._devices:
            if not simulated.device.enabled:
                continue
            for variable in simulated.device.variables:
                signal = simulated.signals.get(variable.name)
                if signal is None:
                    continue
                variable.value = fit_value(variable.ctype, signal.sample(t))

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
