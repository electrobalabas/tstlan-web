import math

from tstlan.devices.simulation.signals import (
    Constant,
    Follow,
    Noise,
    Ramp,
    RandomWalk,
    Sawtooth,
    Sine,
    Square,
    Sum,
)
from tstlan.models import NetVar, NetVarCType, NetVarMode


def test_constant_ignores_time() -> None:
    signal = Constant(3.5)
    assert signal.sample(0.0) == 3.5
    assert signal.sample(99.0) == 3.5


def test_sine_starts_at_offset() -> None:
    assert Sine(amplitude=2.0, period=8.0, offset=10.0).sample(0.0) == 10.0


def test_sine_reaches_peak_at_quarter_period() -> None:
    signal = Sine(amplitude=2.0, period=8.0, offset=10.0)
    assert math.isclose(signal.sample(2.0), 12.0)


def test_sawtooth_rises_from_low_to_high() -> None:
    signal = Sawtooth(period=4.0, low=0.0, high=8.0)
    assert signal.sample(0.0) == 0.0
    assert signal.sample(2.0) == 4.0


def test_sawtooth_wraps_each_period() -> None:
    signal = Sawtooth(period=4.0, low=0.0, high=8.0)
    assert signal.sample(4.0) == 0.0


def test_square_toggles_on_duty() -> None:
    signal = Square(period=10.0, low=0.0, high=1.0, duty=0.5)
    assert signal.sample(1.0) == 1.0
    assert signal.sample(6.0) == 0.0


def test_ramp_is_linear() -> None:
    signal = Ramp(rate=2.0, start=1.0)
    assert signal.sample(0.0) == 1.0
    assert signal.sample(3.0) == 7.0


def test_noise_stays_within_amplitude() -> None:
    signal = Noise(0.5, seed=7)
    assert all(-0.5 <= signal.sample(t) <= 0.5 for t in range(100))


def test_noise_is_reproducible_for_a_seed() -> None:
    first = [Noise(1.0, seed=42).sample(t) for t in range(5)]
    second = [Noise(1.0, seed=42).sample(t) for t in range(5)]
    assert first == second


def test_random_walk_stays_within_bounds() -> None:
    signal = RandomWalk(start=5.0, step=2.0, low=0.0, high=10.0, seed=1)
    assert all(0.0 <= signal.sample(t) <= 10.0 for t in range(200))


def test_sum_adds_terms() -> None:
    assert Sum(Constant(2.0), Constant(3.0)).sample(0.0) == 5.0


def test_add_operator_builds_sum() -> None:
    combined = Constant(2.0) + Constant(5.0)
    assert isinstance(combined, Sum)
    assert combined.sample(0.0) == 7.0


def test_follow_reflects_target_value() -> None:
    target = NetVar("setpoint", NetVarCType.F32, NetVarMode.RW, value=4.0)
    signal = Follow(target)
    assert signal.sample(0.0) == 4.0
    target.value = 9.0
    assert signal.sample(1.0) == 9.0
