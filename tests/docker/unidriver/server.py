import argparse
import ctypes
import json
import socketserver
import threading
import traceback
from pathlib import Path
from typing import Any, cast


class NativeUnidriverIO:
    def __init__(self, library: Path) -> None:
        self._lib = ctypes.CDLL(str(library))
        self._configure()

    def read_bytes(self, handle: int, index: int, size: int) -> bytes:
        buffer = ctypes.create_string_buffer(size)
        _check(self._lib.unidriver_read_bytes(handle, index, buffer, size))
        return bytes(buffer.raw)

    def write_bytes(self, handle: int, index: int, value: bytes) -> None:
        buffer = ctypes.create_string_buffer(value, len(value))
        _check(self._lib.unidriver_write_bytes(handle, index, buffer, len(value)))

    def read_bit(self, handle: int, byte_index: int, bit_index: int) -> bool:
        value = ctypes.c_int()
        _check(
            self._lib.unidriver_read_bit(
                handle, byte_index, bit_index, ctypes.byref(value)
            )
        )
        return bool(value.value)

    def write_bit(
        self, handle: int, byte_index: int, bit_index: int, value: bool
    ) -> None:
        _check(self._lib.unidriver_write_bit(handle, byte_index, bit_index, int(value)))

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


def _check(code: int) -> None:
    if code != 0:
        raise RuntimeError(f"libunidriver returned {code}")


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server = cast("DeviceServer", self.server)
        for line in self.rfile:
            request = json.loads(line)
            with server.lock:
                response = _apply(server.io, request)
            self.wfile.write((json.dumps(response) + "\n").encode())
            self.wfile.flush()


class DeviceServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], io: NativeUnidriverIO) -> None:
        super().__init__(address, Handler)
        self.io = io
        self.lock = threading.Lock()

    def handle_error(self, request: object, client_address: object) -> None:
        print(f"handler error from {client_address}", flush=True)
        traceback.print_exc()


def _apply(io: NativeUnidriverIO, request: dict[str, Any]) -> dict[str, Any]:
    op = request["op"]
    handle = request["handle"]
    if op == "read_bytes":
        return {"data": io.read_bytes(handle, request["index"], request["size"]).hex()}
    if op == "write_bytes":
        io.write_bytes(handle, request["index"], bytes.fromhex(request["data"]))
        return {"ok": True}
    if op == "read_bit":
        return {"value": io.read_bit(handle, request["byte"], request["bit"])}
    if op == "write_bit":
        io.write_bit(handle, request["byte"], request["bit"], request["value"])
        return {"ok": True}
    raise ValueError(f"unknown operation: {op}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9000)
    parser.add_argument("--library", type=Path, required=True)
    args = parser.parse_args()

    server = DeviceServer((args.host, args.port), NativeUnidriverIO(args.library))
    print(f"listening {args.host}:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
