import json
from typing import Any


def encode(message: dict[str, Any]) -> bytes:
    return (json.dumps(message) + "\n").encode()


def decode(line: bytes) -> dict[str, Any]:
    return json.loads(line)
