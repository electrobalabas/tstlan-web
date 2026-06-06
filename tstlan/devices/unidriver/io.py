from typing import Protocol, runtime_checkable


@runtime_checkable
class UnidriverIO(Protocol):
    def read_bytes(self, handle: int, index: int, size: int) -> bytes: ...

    def write_bytes(self, handle: int, index: int, value: bytes) -> None: ...

    def read_bit(self, handle: int, byte_index: int, bit_index: int) -> bool: ...

    def write_bit(
        self, handle: int, byte_index: int, bit_index: int, value: bool
    ) -> None: ...

    def tick(self) -> None: ...

    def is_connected(self, handle: int) -> bool: ...


class InMemoryUnidriverIO:
    """Шов поверх байтовых буферов в памяти — один `bytearray` на хэндл.

    Без сети: «прибор» и бэкенд делят буфер. Буфер растёт под запись и
    дополняется нулями при чтении за границей.
    """

    def __init__(self) -> None:
        self._buffers: dict[int, bytearray] = {}

    def _ensure(self, handle: int, end: int) -> bytearray:
        buffer = self._buffers.setdefault(handle, bytearray())
        if end > len(buffer):
            buffer.extend(bytes(end - len(buffer)))
        return buffer

    def read_bytes(self, handle: int, index: int, size: int) -> bytes:
        buffer = self._ensure(handle, index + size)
        return bytes(buffer[index : index + size])

    def write_bytes(self, handle: int, index: int, value: bytes) -> None:
        buffer = self._ensure(handle, index + len(value))
        buffer[index : index + len(value)] = value

    def read_bit(self, handle: int, byte_index: int, bit_index: int) -> bool:
        buffer = self._ensure(handle, byte_index + 1)
        return bool(buffer[byte_index] >> bit_index & 1)

    def write_bit(
        self, handle: int, byte_index: int, bit_index: int, value: bool
    ) -> None:
        buffer = self._ensure(handle, byte_index + 1)
        mask = 1 << bit_index
        if value:
            buffer[byte_index] |= mask
        else:
            buffer[byte_index] &= ~mask & 0xFF

    def tick(self) -> None:
        pass

    def is_connected(self, handle: int) -> bool:
        return handle in self._buffers
