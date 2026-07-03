"""История значений приборов: кольцевые буферы в памяти процесса.

Точки собирает фоновый сэмплер (см. `run_sampler`); в БД история не пишется —
оперативные значения принадлежат прибору, сервер хранит лишь ограниченное окно
для графиков. Перезапуск сервера историю обнуляет.
"""

import asyncio
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from tstlan.devices.service import DeviceService

SAMPLE_INTERVAL_SECONDS = 1.0
# ~15 минут при шаге в секунду; столько же держит клиентский буфер графиков
MAX_POINTS = 900

History = dict[str, deque["Sample"]]


@dataclass(frozen=True)
class Sample:
    t: float  # серверное время unix, секунды
    values: dict[str, int | float]


def new_history() -> History:
    return {}


def record_snapshot(
    history: History,
    service: DeviceService,
    *,
    clock: Callable[[], float] = time.time,
) -> None:
    """Снять по точке с каждого прибора; недоступный прибор пропускается."""
    for device in service.list_devices():
        try:
            values = {var.name: var.value for var in service.read_values(device.id)}
        except OSError:
            continue
        points = history.setdefault(device.id, deque(maxlen=MAX_POINTS))
        points.append(Sample(clock(), values))


def device_history(history: History, device_id: str) -> list[Sample]:
    return list(history.get(device_id, ()))


async def run_sampler(
    history: History,
    service: DeviceService,
    stop: asyncio.Event,
    *,
    interval: float = SAMPLE_INTERVAL_SECONDS,
) -> None:
    while not stop.is_set():
        record_snapshot(history, service)
        await _wait(stop, interval)


async def _wait(stop: asyncio.Event, interval: float) -> None:
    try:
        await asyncio.wait_for(stop.wait(), timeout=interval)
    except TimeoutError:
        pass
