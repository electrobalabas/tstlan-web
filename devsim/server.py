import argparse
import socketserver
import threading
from pathlib import Path
from typing import Any, cast

import yaml

from tstlan.configs.schemas import ConfigPayload
from tstlan.devices.config_device import device_from_config
from tstlan.devices.runtime import bind_device
from tstlan.devices.unidriver import InMemoryUnidriverIO

from devsim import protocol

HANDLE = 1


def load_payload(path: Path) -> ConfigPayload:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return ConfigPayload.model_validate(data["payload"])


def build_io(payload: ConfigPayload) -> InMemoryUnidriverIO:
    io = InMemoryUnidriverIO()
    bind_device(io, device_from_config("sim", "sim", payload), HANDLE)
    return io


class _Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        server = cast("DeviceServer", self.server)
        for line in self.rfile:
            request: dict[str, Any] = protocol.decode(line)
            with server.lock:
                response = protocol.apply(server.io, request)
            self.wfile.write(protocol.encode(response))
            self.wfile.flush()


class DeviceServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], io: InMemoryUnidriverIO) -> None:
        super().__init__(address, _Handler)
        self.io = io
        self.lock = threading.Lock()


def serve(
    payload: ConfigPayload, host: str = "127.0.0.1", port: int = 0
) -> DeviceServer:
    return DeviceServer((host, port), build_io(payload))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="devsim", description="Тестовый прибор")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    server = serve(load_payload(args.config), args.host, args.port)
    address = server.server_address
    print(f"listening {address[0]}:{address[1]}", flush=True)  # noqa: T201
    server.serve_forever()
