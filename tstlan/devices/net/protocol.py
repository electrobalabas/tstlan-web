"""Минимальный протокол доступа к буферу прибора по TCP — построчный JSON.

Операции отражают шов `UnidriverIO` (read/write bytes|bit). Это транспорт
тест-харнеса для отдельного процесса-прибора, а не TSTLAN: настоящий протокол
приходит вместе с `libunidriver.so` (см. issue про Docker-интеграцию).
"""

import json
from typing import Any

from tstlan.devices.unidriver import UnidriverIO


def encode(message: dict[str, Any]) -> bytes:
    return (json.dumps(message) + "\n").encode()


def decode(line: bytes) -> dict[str, Any]:
    return json.loads(line)


def apply(io: UnidriverIO, request: dict[str, Any]) -> dict[str, Any]:
    """Выполнить запрос над буфером прибора и вернуть ответ."""
    op = request["op"]
    handle = request["handle"]
    if op == "read_bytes":
        data = io.read_bytes(handle, request["index"], request["size"])
        return {"data": data.hex()}
    if op == "write_bytes":
        io.write_bytes(handle, request["index"], bytes.fromhex(request["data"]))
        return {"ok": True}
    if op == "read_bit":
        return {"value": io.read_bit(handle, request["byte"], request["bit"])}
    if op == "write_bit":
        io.write_bit(handle, request["byte"], request["bit"], request["value"])
        return {"ok": True}
    raise ValueError(f"неизвестная операция: {op}")
