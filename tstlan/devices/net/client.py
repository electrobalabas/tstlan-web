from typing import Any

from tstlan.devices.net import protocol


class LazySocketUnidriverIO:
    """Сокет-клиент к процессу-прибору, который соединяется при первом обращении.

    Прибор можно поднять позже сервера: метаданные отдаются сразу, а соединение
    устанавливается на первом чтении/записи и переустанавливается после обрыва.
    """

    def __init__(self, host: str, port: int, *, timeout: float = 5.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._io: SocketUnidriverIO | None = None

    def read_bytes(self, handle: int, index: int, size: int) -> bytes:
        return self._call("read_bytes", handle, index, size)

    def write_bytes(self, handle: int, index: int, value: bytes) -> None:
        self._call("write_bytes", handle, index, value)

    def read_bit(self, handle: int, byte_index: int, bit_index: int) -> bool:
        return self._call("read_bit", handle, byte_index, bit_index)

    def write_bit(
        self, handle: int, byte_index: int, bit_index: int, value: bool
    ) -> None:
        self._call("write_bit", handle, byte_index, bit_index, value)

    def tick(self) -> None:
        pass

    def is_connected(self, handle: int) -> bool:
        return self._io is not None and self._io.is_connected(handle)

    def _call(self, name: str, *args: Any) -> Any:
        try:
            return getattr(self._connect(), name)(*args)
        except OSError:  # ConnectionError -- подкласс OSError
            self._reset()
        # один повтор после переподключения
        return getattr(self._connect(), name)(*args)

    def _connect(self) -> "SocketUnidriverIO":
        if self._io is None:
            self._io = SocketUnidriverIO(self._host, self._port, timeout=self._timeout)
        return self._io

    def _reset(self) -> None:
        if self._io is not None:
            try:
                self._io.close()
            except OSError:
                pass
            self._io = None


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
