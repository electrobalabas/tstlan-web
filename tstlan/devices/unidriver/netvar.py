import struct
from collections.abc import Sequence

from tstlan.configs.schemas import ConfigVar, VarOffset, variable_offsets
from tstlan.devices.unidriver.io import UnidriverIO
from tstlan.models import NetVar, NetVarCType, NetVarMode

# Little-endian: детерминированный порядок байт, совместимый с x86-приборами.
_STRUCT_FORMAT: dict[NetVarCType, str] = {
    NetVarCType.U8: "<B",
    NetVarCType.I8: "<b",
    NetVarCType.U16: "<H",
    NetVarCType.I16: "<h",
    NetVarCType.U32: "<I",
    NetVarCType.I32: "<i",
    NetVarCType.U64: "<Q",
    NetVarCType.I64: "<q",
    NetVarCType.F32: "<f",
    NetVarCType.F64: "<d",
}


class NetVarAccessor:
    """Чтение/запись одной переменной прибора через шов по её адресу."""

    def __init__(
        self, io: UnidriverIO, handle: int, var: NetVar, offset: VarOffset
    ) -> None:
        self._io = io
        self._handle = handle
        self._var = var
        self._offset = offset

    @property
    def name(self) -> str:
        return self._var.name

    @property
    def ctype(self) -> NetVarCType:
        return self._var.ctype

    @property
    def mode(self) -> NetVarMode:
        return self._var.mode

    def get(self) -> int | float:
        if self._var.ctype is NetVarCType.BIT:
            assert self._offset.bit is not None
            return int(
                self._io.read_bit(self._handle, self._offset.byte, self._offset.bit)
            )
        raw = self._io.read_bytes(
            self._handle, self._offset.byte, self._var.ctype.byte_size
        )
        return struct.unpack(_STRUCT_FORMAT[self._var.ctype], raw)[0]

    def set(self, value: int | float) -> None:
        if self._var.ctype is NetVarCType.BIT:
            assert self._offset.bit is not None
            self._io.write_bit(
                self._handle, self._offset.byte, self._offset.bit, bool(value)
            )
            return
        packed = struct.pack(_STRUCT_FORMAT[self._var.ctype], value)
        self._io.write_bytes(self._handle, self._offset.byte, packed)


def build_scheme(
    io: UnidriverIO, handle: int, variables: Sequence[NetVar]
) -> list[NetVarAccessor]:
    """Аксессоры переменных прибора: адрес каждого выводится из порядка и типа."""
    offsets = variable_offsets(
        [ConfigVar(name=var.name, ctype=var.ctype) for var in variables]
    )
    return [
        NetVarAccessor(io, handle, var, offset)
        for var, offset in zip(variables, offsets, strict=True)
    ]
