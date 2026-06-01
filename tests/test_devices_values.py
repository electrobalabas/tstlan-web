import pytest

from tstlan.devices.models import ValueValidationError, coerce_value, fit_value
from tstlan.models import NetVarCType


def test_keeps_integer_within_range() -> None:
    assert coerce_value(NetVarCType.U8, 200) == 200


def test_accepts_lower_range_bound() -> None:
    assert coerce_value(NetVarCType.I8, -128) == -128


def test_accepts_upper_range_bound() -> None:
    assert coerce_value(NetVarCType.I8, 127) == 127


def test_rejects_value_above_range() -> None:
    with pytest.raises(ValueValidationError):
        coerce_value(NetVarCType.U8, 256)


def test_rejects_value_below_range() -> None:
    with pytest.raises(ValueValidationError):
        coerce_value(NetVarCType.U8, -1)


def test_rejects_float_for_integer_type() -> None:
    with pytest.raises(ValueValidationError):
        coerce_value(NetVarCType.U16, 1.5)


def test_rejects_boolean() -> None:
    with pytest.raises(ValueValidationError):
        coerce_value(NetVarCType.U8, True)


def test_converts_integer_to_float_type() -> None:
    assert isinstance(coerce_value(NetVarCType.F32, 3), float)


def test_keeps_float_for_float_type() -> None:
    assert coerce_value(NetVarCType.F64, 1.25) == 1.25


def test_fit_value_saturates_above_range() -> None:
    assert fit_value(NetVarCType.U8, 300.0) == 255


def test_fit_value_saturates_below_range() -> None:
    assert fit_value(NetVarCType.I8, -200.0) == -128


def test_fit_value_rounds_float_to_integer_type() -> None:
    assert fit_value(NetVarCType.U16, 2.6) == 3


def test_fit_value_keeps_float_for_float_type() -> None:
    assert fit_value(NetVarCType.F32, 1.5) == 1.5
