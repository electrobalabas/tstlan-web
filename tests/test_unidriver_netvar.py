import struct

from tstlan.devices.unidriver import InMemoryUnidriverIO, NetVarAccessor, build_scheme
from tstlan.models import NetVar, NetVarCType, NetVarMode


def _scheme(io: InMemoryUnidriverIO, *variables: NetVar) -> dict[str, NetVarAccessor]:
    return {acc.name: acc for acc in build_scheme(io, 1, list(variables))}


def test_round_trip_u32() -> None:
    io = InMemoryUnidriverIO()
    acc = build_scheme(io, 1, [NetVar("n", NetVarCType.U32, NetVarMode.RW)])[0]
    acc.set(123456)
    assert acc.get() == 123456


def test_round_trip_f32_is_float() -> None:
    io = InMemoryUnidriverIO()
    acc = build_scheme(io, 1, [NetVar("v", NetVarCType.F32, NetVarMode.RW)])[0]
    acc.set(1.5)
    assert acc.get() == 1.5
    assert isinstance(acc.get(), float)


def test_bit_round_trip() -> None:
    io = InMemoryUnidriverIO()
    acc = build_scheme(io, 1, [NetVar("b", NetVarCType.BIT, NetVarMode.RW)])[0]
    acc.set(1)
    assert acc.get() == 1


def test_scheme_lays_out_variables_by_offset() -> None:
    io = InMemoryUnidriverIO()
    scheme = _scheme(
        io,
        NetVar("flag", NetVarCType.BIT, NetVarMode.RW),
        NetVar("count", NetVarCType.U32, NetVarMode.RW),
        NetVar("level", NetVarCType.F32, NetVarMode.RW),
    )
    scheme["flag"].set(1)
    scheme["count"].set(7)
    scheme["level"].set(2.5)
    # bit в байте 0, u32 со следующего байта, f32 после него.
    assert io.read_bytes(1, 1, 4) == struct.pack("<I", 7)
    assert io.read_bytes(1, 5, 4) == struct.pack("<f", 2.5)
    assert scheme["flag"].get() == 1
    assert scheme["count"].get() == 7
    assert scheme["level"].get() == 2.5


def test_accessor_exposes_mode_and_ctype() -> None:
    io = InMemoryUnidriverIO()
    acc = build_scheme(io, 1, [NetVar("ro", NetVarCType.U8, NetVarMode.R)])[0]
    assert acc.mode is NetVarMode.R
    assert acc.ctype is NetVarCType.U8
