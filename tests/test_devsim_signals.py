from tstlan.devices.simulation.signals import Sine

from devsim.signals import build_signal


def test_build_signal_maps_kind_and_params() -> None:
    signal = build_signal(
        {"kind": "sine", "amplitude": 0.5, "period": 12.0, "offset": 220.0}
    )
    assert isinstance(signal, Sine)
    assert signal.sample(0.0) == 220.0  # sin(0) == 0 -> только offset


def test_build_signal_sums_plus_terms() -> None:
    signal = build_signal(
        {"kind": "constant", "value": 1.0, "plus": [{"kind": "constant", "value": 2.0}]}
    )
    assert signal.sample(0.0) == 3.0
