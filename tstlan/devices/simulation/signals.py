import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tstlan.models import NetVar


class Signal(ABC):
    @abstractmethod
    def sample(self, t: float) -> float:
        """Значение регистра в момент времени `t` (секунды от старта)."""

    def __add__(self, other: "Signal") -> "Signal":
        return Sum(self, other)


class Sum(Signal):
    """Сумма сигналов (Composite). Несущая частота + шум, тренд + колебание."""

    def __init__(self, *terms: Signal) -> None:
        self._terms = terms

    def sample(self, t: float) -> float:
        return sum(term.sample(t) for term in self._terms)


@dataclass(frozen=True)
class Constant(Signal):
    value: float

    def sample(self, t: float) -> float:
        return self.value


@dataclass(frozen=True)
class Sine(Signal):
    amplitude: float
    period: float
    offset: float = 0.0
    phase: float = 0.0

    def sample(self, t: float) -> float:
        return self.offset + self.amplitude * math.sin(
            2.0 * math.pi * t / self.period + self.phase
        )


@dataclass(frozen=True)
class Sawtooth(Signal):
    period: float
    low: float = 0.0
    high: float = 1.0

    def sample(self, t: float) -> float:
        fraction = (t % self.period) / self.period
        return self.low + (self.high - self.low) * fraction


@dataclass(frozen=True)
class Square(Signal):
    period: float
    low: float = 0.0
    high: float = 1.0
    duty: float = 0.5

    def sample(self, t: float) -> float:
        fraction = (t % self.period) / self.period
        return self.high if fraction < self.duty else self.low


@dataclass(frozen=True)
class Ramp(Signal):
    rate: float
    start: float = 0.0

    def sample(self, t: float) -> float:
        return self.start + self.rate * t


class Noise(Signal):
    """Белый шум в диапазоне [-amplitude, amplitude]. Seed делает прогон воспроизводимым."""

    def __init__(self, amplitude: float, *, seed: int = 0) -> None:
        self._amplitude = amplitude
        self._rng = random.Random(seed)

    def sample(self, t: float) -> float:
        return self._rng.uniform(-self._amplitude, self._amplitude)


class RandomWalk(Signal):
    """Случайное блуждание с фиксацией в коридоре [low, high]."""

    def __init__(
        self, *, start: float, step: float, low: float, high: float, seed: int = 0
    ) -> None:
        self._value = start
        self._step = step
        self._low = low
        self._high = high
        self._rng = random.Random(seed)

    def sample(self, t: float) -> float:
        self._value += self._rng.uniform(-self._step, self._step)
        self._value = min(self._high, max(self._low, self._value))
        return self._value


class Follow(Signal):
    """Повторяет текущее значение другого регистра."""

    def __init__(self, target: NetVar) -> None:
        self._target = target

    def sample(self, t: float) -> float:
        return float(self._target.value)
