from enum import StrEnum


class NetVarCType(StrEnum):
    BIT = "bit"
    U8 = "u8"
    I8 = "i8"
    U16 = "u16"
    I16 = "i16"
    U32 = "u32"
    I32 = "i32"
    F32 = "f32"
    F64 = "f64"

    @property
    def byte_size(self) -> int:
        """Размер значения в байтах. Переменные лежат в памяти прибора
        последовательно, поэтому смещение каждой выводится из суммы размеров
        предыдущих — отдельно хранить адрес не нужно."""
        return _C_TYPE_BYTE_SIZE[self]


_C_TYPE_BYTE_SIZE: dict[NetVarCType, int] = {
    NetVarCType.BIT: 1,
    NetVarCType.U8: 1,
    NetVarCType.I8: 1,
    NetVarCType.U16: 2,
    NetVarCType.I16: 2,
    NetVarCType.U32: 4,
    NetVarCType.I32: 4,
    NetVarCType.F32: 4,
    NetVarCType.F64: 8,
}


class NetVarMode(StrEnum):
    R = "r"
    W = "w"
    RW = "rw"


class NetVar:
    def __init__(
        self,
        name: str,
        ctype: NetVarCType,
        mode: NetVarMode,
        value: int | float = 0,
    ) -> None:
        self.name = name
        self.ctype = ctype
        self.mode = mode
        self.value: int | float = value
