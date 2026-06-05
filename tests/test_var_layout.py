from tstlan.configs.schemas import ConfigVar, variable_offsets
from tstlan.models import NetVarCType


def test_byte_size_matches_ctype() -> None:
    assert NetVarCType.BIT.byte_size == 1
    assert NetVarCType.U16.byte_size == 2
    assert NetVarCType.U32.byte_size == 4
    assert NetVarCType.F64.byte_size == 8


def test_variable_offsets_accumulate_sequentially_by_type() -> None:
    variables = [
        ConfigVar(name="a", ctype=NetVarCType.BIT),
        ConfigVar(name="b", ctype=NetVarCType.U32),
        ConfigVar(name="c", ctype=NetVarCType.F32),
    ]
    # bit(1) -> u32(4) -> f32: смещения 0, 1, 5.
    assert variable_offsets(variables) == [0, 1, 5]


def test_variable_offsets_empty() -> None:
    assert variable_offsets([]) == []
