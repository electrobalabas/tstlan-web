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
