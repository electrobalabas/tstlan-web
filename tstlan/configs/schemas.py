from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, NamedTuple

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


class VarOffset(NamedTuple):
    """Адрес переменной: байтовое смещение и, для bit, номер бита в байте."""

    byte: int
    bit: int | None = None


def variable_offsets(variables: Sequence[ConfigVar]) -> list[VarOffset]:
    """Адреса переменных: смещение выводится из порядка и типа"""
    offsets: list[VarOffset] = []
    prev: VarOffset | None = None
    prev_ctype: NetVarCType | None = None
    for var in variables:
        is_bit = var.ctype is NetVarCType.BIT
        if prev is None or prev_ctype is None:
            cur = VarOffset(0, 0 if is_bit else None)
        elif prev_ctype is NetVarCType.BIT and is_bit:
            assert prev.bit is not None
            cur = (
                VarOffset(prev.byte + 1, 0)
                if prev.bit >= 7
                else VarOffset(prev.byte, prev.bit + 1)
            )
        else:
            cur = VarOffset(prev.byte + prev_ctype.byte_size, 0 if is_bit else None)
        offsets.append(cur)
        prev, prev_ctype = cur, var.ctype
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
        "sync_id": config.sync_id,
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
    sync_id: str
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
