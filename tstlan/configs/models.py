from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from tstlan.auth.models import User, utcnow
from tstlan.db import Base


class ConfigVisibility(StrEnum):
    PRIVATE = "private"
    SHARED = "shared"
    PUBLIC = "public"


class SharePermission(StrEnum):
    READ = "read"
    WRITE = "write"


def _enum_column(enum_cls: type[StrEnum]) -> SAEnum:
    return SAEnum(
        enum_cls,
        native_enum=False,
        length=16,
        values_callable=lambda enum: [member.value for member in enum],
    )


class DeviceConfig(Base):
    """Конфигурация-профиль TSTLAN, привязанная к типу прибора.

    Аналог per-device `.ini` десктопного TSTLAN: подключение и вид переменных
    хранятся в `payload`, владелец и видимость задают доступ.
    """

    __tablename__ = "device_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    device_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    visibility: Mapped[ConfigVisibility] = mapped_column(
        _enum_column(ConfigVisibility), default=ConfigVisibility.PRIVATE
    )
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(foreign_keys=[owner_id], lazy="selectin")
    shares: Mapped[list["ConfigShare"]] = relationship(
        back_populates="config",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ConfigShare(Base):
    """Точечный грант доступа к конфигу одному пользователю (read|write)."""

    __tablename__ = "config_shares"

    id: Mapped[int] = mapped_column(primary_key=True)
    config_id: Mapped[int] = mapped_column(
        ForeignKey("device_configs.id", ondelete="CASCADE"), index=True
    )
    grantee_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    permission: Mapped[SharePermission] = mapped_column(
        _enum_column(SharePermission), default=SharePermission.READ
    )

    config: Mapped[DeviceConfig] = relationship(back_populates="shares")
    grantee: Mapped[User] = relationship(foreign_keys=[grantee_id], lazy="selectin")

    __table_args__ = (
        UniqueConstraint("config_id", "grantee_id", name="uq_config_share_grantee"),
    )
