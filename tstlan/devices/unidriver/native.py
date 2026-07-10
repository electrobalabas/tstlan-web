from __future__ import annotations

import ctypes
from pathlib import Path


class NativeUnidriverIO:
    """UnidriverIO adapter backed by a C shared library.

    The expected ABI is intentionally tiny and mirrors the Python protocol:
    read/write bytes, read/write bit, tick, and connection state.
    """

    def __init__(self, library: str | Path) -> None:
        self._lib = ctypes.CDLL(str(library))
        self._configure()

    def read_bytes(self, handle: int, index: int, size: int) -> bytes:
        buffer = ctypes.create_string_buffer(size)
        self._check(
            self._lib.unidriver_read_bytes(handle, index, buffer, size),
            "unidriver_read_bytes",
        )
        return bytes(buffer.raw)

    def write_bytes(self, handle: int, index: int, value: bytes) -> None:
        buffer = ctypes.create_string_buffer(value, len(value))
        self._check(
            self._lib.unidriver_write_bytes(handle, index, buffer, len(value)),
            "unidriver_write_bytes",
        )

    def read_bit(self, handle: int, byte_index: int, bit_index: int) -> bool:
        value = ctypes.c_int()
        self._check(
            self._lib.unidriver_read_bit(
                handle, byte_index, bit_index, ctypes.byref(value)
            ),
            "unidriver_read_bit",
        )
        return bool(value.value)

    def write_bit(
        self, handle: int, byte_index: int, bit_index: int, value: bool
    ) -> None:
        self._check(
            self._lib.unidriver_write_bit(handle, byte_index, bit_index, int(value)),
            "unidriver_write_bit",
        )

    def tick(self) -> None:
        self._check(self._lib.unidriver_tick(), "unidriver_tick")

    def is_connected(self, handle: int) -> bool:
        return bool(self._lib.unidriver_is_connected(handle))

    def _configure(self) -> None:
        self._lib.unidriver_read_bytes.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        self._lib.unidriver_read_bytes.restype = ctypes.c_int
        self._lib.unidriver_write_bytes.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_int,
        ]
        self._lib.unidriver_write_bytes.restype = ctypes.c_int
        self._lib.unidriver_read_bit.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_int),
        ]
        self._lib.unidriver_read_bit.restype = ctypes.c_int
        self._lib.unidriver_write_bit.argtypes = [
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
        ]
        self._lib.unidriver_write_bit.restype = ctypes.c_int
        self._lib.unidriver_tick.argtypes = []
        self._lib.unidriver_tick.restype = ctypes.c_int
        self._lib.unidriver_is_connected.argtypes = [ctypes.c_int]
        self._lib.unidriver_is_connected.restype = ctypes.c_int

    def _check(self, code: int, operation: str) -> None:
        if code != 0:
            raise OSError(f"{operation} failed with code {code}")
