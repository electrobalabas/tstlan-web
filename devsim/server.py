import argparse
import socketserver
import threading
import time
from pathlib import Path
from typing import Any, cast

from tstlan.devices.scenario import Scenario, device_from_scenario, load_scenario
from tstlan.devices.simulation import SimulatedDevice, SimulationEngine
from tstlan.devices.unidriver import InMemoryUnidriverIO

from devsim import protocol
from devsim.signals import build_signal

HANDLE = 1
_TICK_SECONDS = 0.5


def build_simulated(scenario: Scenario, device_id: str = "sim") -> SimulatedDevice:
    signals = {name: build_signal(spec) for name, spec in scenario.signals.items()}
    return SimulatedDevice(device_from_scenario(scenario, device_id), signals, HANDLE)


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


def serve(scenario: Scenario, host: str = "127.0.0.1", port: int = 0) -> DeviceServer:
    io = InMemoryUnidriverIO()
    engine = SimulationEngine(io, [build_simulated(scenario)], interval=_TICK_SECONDS)
    engine.tick(0.0)  # опубликовать стартовые значения сенсоров в буфер
    server = DeviceServer((host, port), io)
    _drive(server, engine)
    return server


def _drive(server: DeviceServer, engine: SimulationEngine) -> None:
    def loop() -> None:
        start = time.monotonic()
        while True:
            with server.lock:
                engine.tick(time.monotonic() - start)
            time.sleep(_TICK_SECONDS)

    threading.Thread(target=loop, daemon=True).start()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="devsim", description="Тестовый прибор-эмулятор"
    )
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args(argv)

    server = serve(load_scenario(args.scenario), args.host, args.port)
    address = server.server_address
    print(f"listening {address[0]}:{address[1]}", flush=True)  # noqa: T201
    server.serve_forever()
