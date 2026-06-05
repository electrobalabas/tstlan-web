from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from tstlan.configs.models import (
    ConfigShare,
    ConfigVisibility,
    DeviceConfig,
    SharePermission,
)
from tstlan.models import NetVarCType


class Access(StrEnum):
    """Эффективный доступ вызывающего пользователя к конфигу."""

    OWNER = "owner"
    WRITE = "write"
    READ = "read"


Transport = Literal["ethernet", "gpib", "com", "modbus_tcp", "modbus_udp"]


class ModbusMap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    discrete_inputs_bytes: int = 0
    coils_bytes: int = 0
    holding_registers: int = 0
    input_registers: int = 0


class ConnectionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transport: Transport = "ethernet"
    ip: str | None = None
    port: int | None = None
    gpib_addr: int | None = None
    com_name: str | None = None
    ip_request: str | None = None
    poll_period_ms: int = 200
    modbus: ModbusMap | None = None
    params: dict[str, str] = Field(default_factory=dict)


class ConfigVar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    ctype: NetVarCType
    graph: bool = False
    category: str = ""


def variable_offsets(variables: Sequence[ConfigVar]) -> list[int]:
    """Смещения переменных в памяти прибора. Список упорядочен и читается
    последовательно, поэтому смещение N-й переменной — это сумма размеров всех
    предыдущих (размер задаёт ctype). Адрес отдельно не храним."""
    offsets: list[int] = []
    cursor = 0
    for var in variables:
        offsets.append(cursor)
        cursor += var.ctype.byte_size
    return offsets


class ConfigPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection: ConnectionSettings = Field(default_factory=ConnectionSettings)
    variables: list[ConfigVar] = Field(default_factory=list)


class ConfigCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    device_type: str
    payload: ConfigPayload = Field(default_factory=ConfigPayload)
    visibility: ConfigVisibility = ConfigVisibility.PRIVATE


class ConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    payload: ConfigPayload | None = None
    visibility: ConfigVisibility | None = None


class ShareInfo(BaseModel):
    login: str
    permission: SharePermission

    @classmethod
    def from_share(cls, share: ConfigShare) -> "ShareInfo":
        return cls(login=share.grantee.login, permission=share.permission)


class ShareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    login: str
    permission: SharePermission = SharePermission.READ


def _config_fields(config: DeviceConfig, access: Access) -> dict[str, Any]:
    return {
        "id": config.id,
        "name": config.name,
        "device_type": config.device_type,
        "visibility": config.visibility,
        "owner_login": config.owner.login,
        "access": access,
        "created_at": config.created_at,
        "updated_at": config.updated_at,
    }


class ConfigView(BaseModel):
    id: int
    name: str
    device_type: str
    visibility: ConfigVisibility
    owner_login: str
    access: Access
    created_at: datetime
    updated_at: datetime


class ConfigSummary(ConfigView):
    @classmethod
    def from_config(cls, config: DeviceConfig, access: Access) -> "ConfigSummary":
        return cls(**_config_fields(config, access))


class ConfigDetail(ConfigView):
    payload: ConfigPayload
    shares: list[ShareInfo]

    @classmethod
    def from_config(cls, config: DeviceConfig, access: Access) -> "ConfigDetail":
        # Гранты видны только тому, кто управляет конфигом.
        shares = (
            [ShareInfo.from_share(share) for share in config.shares]
            if access is Access.OWNER
            else []
        )
        return cls(
            **_config_fields(config, access),
            payload=ConfigPayload.model_validate(config.payload),
            shares=shares,
        )
