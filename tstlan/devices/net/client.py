from typing import Any

from tstlan.devices.net import protocol


class SocketUnidriverIO:
    def __init__(self, host: str, port: int, *, timeout: float = 5.0) -> None:
        import socket

        self._sock = socket.create_connection((host, port), timeout=timeout)
        self._file = self._sock.makefile("rwb")
        self._connected = True

    def _request(self, message: dict[str, Any]) -> dict[str, Any]:
        self._file.write(protocol.encode(message))
        self._file.flush()
        line = self._file.readline()
        if not line:
            self._connected = False
            raise ConnectionError("прибор закрыл соединение")
        return protocol.decode(line)

    def read_bytes(self, handle: int, index: int, size: int) -> bytes:
        message = {"op": "read_bytes", "handle": handle, "index": index, "size": size}
        return bytes.fromhex(self._request(message)["data"])

    def write_bytes(self, handle: int, index: int, value: bytes) -> None:
        self._request(
            {"op": "write_bytes", "handle": handle, "index": index, "data": value.hex()}
        )

    def read_bit(self, handle: int, byte_index: int, bit_index: int) -> bool:
        message = {
            "op": "read_bit",
            "handle": handle,
            "byte": byte_index,
            "bit": bit_index,
        }
        return bool(self._request(message)["value"])

    def write_bit(
        self, handle: int, byte_index: int, bit_index: int, value: bool
    ) -> None:
        self._request(
            {
                "op": "write_bit",
                "handle": handle,
                "byte": byte_index,
                "bit": bit_index,
                "value": value,
            }
        )

    def tick(self) -> None:
        pass

    def is_connected(self, handle: int) -> bool:
        return self._connected

    def close(self) -> None:
        self._file.close()
        self._sock.close()
        self._connected = False
