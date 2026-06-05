from tstlan.configs.schemas import ConfigVar, VarOffset, variable_offsets
from tstlan.models import NetVarCType


def test_byte_size_matches_ctype() -> None:
    assert NetVarCType.BIT.byte_size == 1
    assert NetVarCType.U16.byte_size == 2
    assert NetVarCType.U32.byte_size == 4
    assert NetVarCType.F64.byte_size == 8


def test_variable_offsets_advance_by_type() -> None:
    variables = [
        ConfigVar(name="a", ctype=NetVarCType.BIT),
        ConfigVar(name="b", ctype=NetVarCType.U32),
        ConfigVar(name="c", ctype=NetVarCType.F32),
    ]
    # bit(байт 0) -> u32(байт 1) -> f32(байт 5).
    assert variable_offsets(variables) == [
        VarOffset(0, 0),
        VarOffset(1, None),
        VarOffset(5, None),
    ]


def test_variable_offsets_pack_bits_into_bytes() -> None:
    variables = [
        ConfigVar(name="b0", ctype=NetVarCType.BIT),
        ConfigVar(name="b1", ctype=NetVarCType.BIT),
        ConfigVar(name="b2", ctype=NetVarCType.BIT),
        ConfigVar(name="r", ctype=NetVarCType.U32),
    ]
    # Три бита делят байт 0, u32 идёт со следующего байта.
    assert variable_offsets(variables) == [
        VarOffset(0, 0),
        VarOffset(0, 1),
        VarOffset(0, 2),
        VarOffset(1, None),
    ]


def test_variable_offsets_wrap_bits_after_eight() -> None:
    variables = [ConfigVar(name=f"b{i}", ctype=NetVarCType.BIT) for i in range(9)]
    offsets = variable_offsets(variables)
    assert offsets[7] == VarOffset(0, 7)
    assert offsets[8] == VarOffset(1, 0)


def test_variable_offsets_empty() -> None:
    assert variable_offsets([]) == []
