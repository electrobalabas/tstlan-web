from dataclasses import dataclass, field
from enum import StrEnum

from tstlan.models import NetVar, NetVarCType


class DeviceStatus(StrEnum):
    OK = "ok"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class Device:
    id: str
    name: str
    type: str
    enabled: bool
    status: DeviceStatus
    variables: list[NetVar] = field(default_factory=list)


class ValueValidationError(ValueError):
    pass


_INT_RANGES: dict[NetVarCType, tuple[int, int]] = {
    NetVarCType.BIT: (0, 1),
    NetVarCType.U8: (0, 0xFF),
    NetVarCType.I8: (-0x80, 0x7F),
    NetVarCType.U16: (0, 0xFFFF),
    NetVarCType.I16: (-0x8000, 0x7FFF),
    NetVarCType.U32: (0, 0xFFFFFFFF),
    NetVarCType.I32: (-0x80000000, 0x7FFFFFFF),
}
_FLOAT_TYPES = frozenset({NetVarCType.F32, NetVarCType.F64})


def coerce_value(ctype: NetVarCType, value: int | float) -> int | float:
    if isinstance(value, bool):
        raise ValueValidationError(f"{ctype} не принимает логическое значение")
    if ctype in _FLOAT_TYPES:
        return float(value)
    if not isinstance(value, int):
        raise ValueValidationError(
            f"{ctype} требует целое значение, получено {value!r}"
        )
    low, high = _INT_RANGES[ctype]
    if not low <= value <= high:
        raise ValueValidationError(f"{value} вне диапазона {ctype} [{low}, {high}]")
    return value


def fit_value(ctype: NetVarCType, value: float) -> int | float:
    if ctype in _FLOAT_TYPES:
        return float(value)
    low, high = _INT_RANGES[ctype]
    return max(low, min(high, round(value)))
