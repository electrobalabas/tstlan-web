from collections.abc import Callable
from typing import Any

from tstlan.devices.simulation.signals import (
    Constant,
    Noise,
    Ramp,
    RandomWalk,
    Sawtooth,
    Signal,
    Sine,
    Square,
)

_FACTORIES: dict[str, Callable[[dict[str, Any]], Signal]] = {
    "constant": lambda p: Constant(**p),
    "sine": lambda p: Sine(**p),
    "sawtooth": lambda p: Sawtooth(**p),
    "square": lambda p: Square(**p),
    "ramp": lambda p: Ramp(**p),
    "noise": lambda p: Noise(**p),
    "random_walk": lambda p: RandomWalk(**p),
}


def build_signal(spec: dict[str, Any]) -> Signal:
    params = dict(spec)
    kind = params.pop("kind")
    # plus складывает несколько сигналов: несущая + шум, тренд + колебание
    terms = params.pop("plus", [])
    signal = _FACTORIES[kind](params)
    for term in terms:
        signal = signal + build_signal(term)
    return signal
