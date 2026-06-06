from dataclasses import dataclass
from typing import Any

from tstlan.auth.models import Role
from tstlan.configs.models import ConfigVisibility, SharePermission


@dataclass(frozen=True)
class SeedUser:
    login: str
    password: str
    role: Role = Role.USER


@dataclass(frozen=True)
class SeedShare:
    login: str
    permission: SharePermission = SharePermission.READ


@dataclass(frozen=True)
class SeedConfig:
    owner: str
    name: str
    device_type: str
    payload: dict[str, Any]
    visibility: ConfigVisibility = ConfigVisibility.PRIVATE
    shares: tuple[SeedShare, ...] = ()


USERS: list[SeedUser] = [
    SeedUser("admin", "admin123", Role.ADMIN),
    SeedUser("engineer", "engineer123", Role.DEV),
    SeedUser("operator", "operator123"),
    SeedUser("viewer", "viewer123"),
]


def _connection(ip: str, port: int) -> dict[str, Any]:
    return {"transport": "ethernet", "ip": ip, "port": port, "poll_period_ms": 200}


CONFIGS: list[SeedConfig] = [
    SeedConfig(
        owner="engineer",
        name="Стенд мультиметра",
        device_type="multimeter",
        visibility=ConfigVisibility.PUBLIC,
        payload={
            "connection": _connection("192.168.0.10", 9001),
            "variables": [
                {"name": "voltage", "ctype": "f32", "graph": True},
                {"name": "current", "ctype": "f32", "graph": True},
                {"name": "samples", "ctype": "u32"},
                {"name": "range", "ctype": "u8"},
                {"name": "reset", "ctype": "u8"},
            ],
        },
    ),
    SeedConfig(
        owner="operator",
        name="Калибратор линии",
        device_type="calibrator",
        payload={
            "connection": _connection("192.168.0.11", 9002),
            "variables": [
                {"name": "setpoint", "ctype": "f32"},
                {"name": "output", "ctype": "f32", "graph": True},
                {"name": "output_on", "ctype": "u8"},
            ],
        },
        shares=(
            SeedShare("viewer"),
            SeedShare("engineer", SharePermission.WRITE),
        ),
    ),
    SeedConfig(
        owner="viewer",
        name="Личный термостат",
        device_type="thermostat",
        payload={
            "connection": _connection("192.168.0.12", 9003),
            "variables": [
                {
                    "name": "temperature",
                    "ctype": "f32",
                    "graph": True,
                    "category": "Климат",
                },
                {"name": "heater", "ctype": "u8"},
                {"name": "setpoint", "ctype": "f32"},
            ],
        },
    ),
]
