from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tstlan.auth.models import User
from tstlan.configs.models import ConfigShare, ConfigVisibility, DeviceConfig

BUNDLE_VERSION = 1
DEVICE_CONFIG_FIELDS = ("name", "device_type", "payload", "visibility")
ConflictPolicy = Literal["copy", "server", "field"]


class BundleError(Exception):
    pass


class ImportBlocked(BundleError):
    pass


class TripAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    SKIP = "skip"
    CONFLICT = "conflict"


class ConfigSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sync_id: str
    owner_login: str
    name: str
    device_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    visibility: ConfigVisibility = ConfigVisibility.PRIVATE


class BundleManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: str = "tstlan.trip.bundle"
    version: int = BUNDLE_VERSION
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    includes: list[str] = Field(default_factory=lambda: ["device_configs"])


@dataclass(frozen=True)
class ConfigPlanItem:
    action: TripAction
    sync_id: str
    name: str
    details: list[str] = field(default_factory=list)
    conflict_fields: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ImportPlan:
    items: list[ConfigPlanItem]

    @property
    def creates(self) -> int:
        return self._count(TripAction.CREATE)

    @property
    def updates(self) -> int:
        return self._count(TripAction.UPDATE)

    @property
    def skips(self) -> int:
        return self._count(TripAction.SKIP)

    @property
    def conflicts(self) -> int:
        return self._count(TripAction.CONFLICT)

    def _count(self, action: TripAction) -> int:
        return sum(1 for item in self.items if item.action is action)


async def snapshot_device_configs(db: AsyncSession) -> list[ConfigSnapshot]:
    result = await db.execute(
        select(DeviceConfig)
        .options(
            selectinload(DeviceConfig.owner),
            selectinload(DeviceConfig.shares).selectinload(ConfigShare.grantee),
        )
        .order_by(DeviceConfig.sync_id)
    )
    configs = result.scalars().unique().all()
    return [
        ConfigSnapshot(
            sync_id=config.sync_id,
            owner_login=config.owner.login,
            name=config.name,
            device_type=config.device_type,
            payload=config.payload,
            visibility=_portable_visibility(config.visibility),
        )
        for config in configs
    ]


def write_export_bundle(path: Path, base: list[ConfigSnapshot]) -> None:
    _write_bundle(path, base=base, field_configs=None)


def write_pack_bundle(
    path: Path, *, base_bundle: Path, field_configs: list[ConfigSnapshot]
) -> None:
    base = read_bundle(base_bundle).base
    _write_bundle(path, base=base, field_configs=field_configs)


@dataclass(frozen=True)
class TripBundle:
    manifest: BundleManifest
    base: list[ConfigSnapshot]
    field: list[ConfigSnapshot] | None


def read_bundle(path: Path) -> TripBundle:
    with zipfile.ZipFile(path) as archive:
        manifest = _read_json(archive, "manifest.json")
        base = _read_json(archive, "base/device_configs.json")
        field_configs = (
            _read_json(archive, "field/device_configs.json")
            if "field/device_configs.json" in archive.namelist()
            else None
        )
    parsed_manifest = BundleManifest.model_validate(manifest)
    if parsed_manifest.kind != "tstlan.trip.bundle":
        raise BundleError(f"unsupported bundle kind: {parsed_manifest.kind}")
    if parsed_manifest.version != BUNDLE_VERSION:
        raise BundleError(f"unsupported bundle version: {parsed_manifest.version}")
    return TripBundle(
        manifest=parsed_manifest,
        base=[ConfigSnapshot.model_validate(item) for item in base],
        field=(
            [ConfigSnapshot.model_validate(item) for item in field_configs]
            if field_configs is not None
            else None
        ),
    )


async def plan_import(db: AsyncSession, bundle_path: Path) -> ImportPlan:
    bundle = read_bundle(bundle_path)
    if bundle.field is None:
        raise ImportBlocked("bundle does not contain field/device_configs.json")
    prod = await snapshot_device_configs(db)
    return build_import_plan(bundle.base, bundle.field, prod)


def build_import_plan(
    base: list[ConfigSnapshot],
    field_configs: list[ConfigSnapshot],
    prod: list[ConfigSnapshot],
) -> ImportPlan:
    base_by_sync = _index(base, "base")
    field_by_sync = _index(field_configs, "field")
    prod_by_sync = _index(prod, "prod")
    items: list[ConfigPlanItem] = []

    for sync_id, field_config in field_by_sync.items():
        base_config = base_by_sync.get(sync_id)
        prod_config = prod_by_sync.get(sync_id)
        name = field_config.name
        if base_config is None:
            if prod_config is None:
                items.append(
                    ConfigPlanItem(TripAction.CREATE, sync_id, name, ["new field config"])
                )
            elif _snapshot_values(prod_config) == _snapshot_values(field_config):
                items.append(ConfigPlanItem(TripAction.SKIP, sync_id, name, ["already exists"]))
            else:
                items.append(
                    ConfigPlanItem(
                        TripAction.CONFLICT,
                        sync_id,
                        name,
                        ["created independently in field and prod"],
                        list(DEVICE_CONFIG_FIELDS),
                    )
                )
            continue

        if prod_config is None:
            if _snapshot_values(base_config) == _snapshot_values(field_config):
                items.append(ConfigPlanItem(TripAction.SKIP, sync_id, name, ["deleted in prod"]))
            else:
                items.append(
                    ConfigPlanItem(
                        TripAction.CONFLICT,
                        sync_id,
                        name,
                        ["changed in field but missing in prod"],
                        list(DEVICE_CONFIG_FIELDS),
                    )
                )
            continue

        changed_fields: list[str] = []
        conflict_fields: list[str] = []
        for field_name in DEVICE_CONFIG_FIELDS:
            base_value = getattr(base_config, field_name)
            field_value = getattr(field_config, field_name)
            prod_value = getattr(prod_config, field_name)
            if field_value == base_value:
                continue
            if prod_value == base_value or prod_value == field_value:
                changed_fields.append(field_name)
            else:
                conflict_fields.append(field_name)

        if conflict_fields:
            items.append(
                ConfigPlanItem(
                    TripAction.CONFLICT,
                    sync_id,
                    name,
                    ["field and prod changed different values"],
                    conflict_fields,
                )
            )
        elif changed_fields:
            items.append(
                ConfigPlanItem(TripAction.UPDATE, sync_id, name, changed_fields)
            )
        else:
            items.append(ConfigPlanItem(TripAction.SKIP, sync_id, name, ["unchanged"]))

    return ImportPlan(items)


async def apply_import(
    db: AsyncSession,
    bundle_path: Path,
    *,
    conflict_policy: ConflictPolicy = "copy",
) -> ImportPlan:
    if conflict_policy not in ("copy", "server", "field"):
        raise ValueError(f"unknown conflict policy: {conflict_policy}")
    bundle = read_bundle(bundle_path)
    if bundle.field is None:
        raise ImportBlocked("bundle does not contain field/device_configs.json")

    prod = await _load_prod_configs(db)
    plan = build_import_plan(
        bundle.base,
        bundle.field,
        [_snapshot_from_model(config) for config in prod],
    )
    field_by_sync = {item.sync_id: item for item in bundle.field}
    prod_by_sync = {config.sync_id: config for config in prod}

    for item in plan.items:
        field_config = field_by_sync[item.sync_id]
        prod_config = prod_by_sync.get(item.sync_id)
        if item.action is TripAction.CREATE:
            await _create_config(db, field_config)
        elif item.action is TripAction.UPDATE and prod_config is not None:
            _apply_snapshot(prod_config, field_config)
        elif item.action is TripAction.CONFLICT:
            if conflict_policy == "copy":
                await _create_config(db, field_config, as_copy=True)
            elif conflict_policy == "field" and prod_config is not None:
                _apply_snapshot(prod_config, field_config)

    await db.commit()
    return plan


async def _load_prod_configs(db: AsyncSession) -> list[DeviceConfig]:
    result = await db.execute(
        select(DeviceConfig)
        .options(selectinload(DeviceConfig.owner))
        .order_by(DeviceConfig.sync_id)
    )
    return list(result.scalars().unique().all())


def _write_bundle(
    path: Path,
    *,
    base: list[ConfigSnapshot],
    field_configs: list[ConfigSnapshot] | None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = BundleManifest()
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "manifest.json", _json_dumps(manifest.model_dump(mode="json"))
        )
        archive.writestr(
            "base/device_configs.json",
            _json_dumps([item.model_dump(mode="json") for item in base]),
        )
        if field_configs is not None:
            archive.writestr(
                "field/device_configs.json",
                _json_dumps([item.model_dump(mode="json") for item in field_configs]),
            )


def _read_json(archive: zipfile.ZipFile, name: str) -> Any:
    try:
        with archive.open(name) as handle:
            return json.loads(handle.read().decode("utf-8"))
    except KeyError as exc:
        raise BundleError(f"bundle is missing {name}") from exc


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)


def _index(items: list[ConfigSnapshot], label: str) -> dict[str, ConfigSnapshot]:
    result: dict[str, ConfigSnapshot] = {}
    for item in items:
        if item.sync_id in result:
            raise BundleError(f"duplicate sync_id in {label}: {item.sync_id}")
        result[item.sync_id] = item
    return result


def _snapshot_values(snapshot: ConfigSnapshot) -> dict[str, Any]:
    return {field_name: getattr(snapshot, field_name) for field_name in DEVICE_CONFIG_FIELDS}


def _snapshot_from_model(config: DeviceConfig) -> ConfigSnapshot:
    return ConfigSnapshot(
        sync_id=config.sync_id,
        owner_login=config.owner.login,
        name=config.name,
        device_type=config.device_type,
        payload=config.payload,
        visibility=_portable_visibility(config.visibility),
    )


async def _create_config(
    db: AsyncSession, snapshot: ConfigSnapshot, *, as_copy: bool = False
) -> None:
    owner = await _owner_by_login(db, snapshot.owner_login)
    name = snapshot.name if not as_copy else f"{snapshot.name} (field copy)"
    values = dict(
        owner_id=owner.id,
        name=name,
        device_type=snapshot.device_type,
        payload=snapshot.payload,
        visibility=_portable_visibility(snapshot.visibility),
    )
    if not as_copy:
        values["sync_id"] = snapshot.sync_id
    db.add(DeviceConfig(**values))


async def _owner_by_login(db: AsyncSession, login: str) -> User:
    owner = (await db.execute(select(User).where(User.login == login))).scalar_one_or_none()
    if owner is None:
        raise ImportBlocked(f"owner does not exist in prod database: {login}")
    return owner


def _apply_snapshot(config: DeviceConfig, snapshot: ConfigSnapshot) -> None:
    config.name = snapshot.name
    config.device_type = snapshot.device_type
    config.payload = snapshot.payload
    config.visibility = _portable_visibility(snapshot.visibility)


def _portable_visibility(visibility: ConfigVisibility) -> ConfigVisibility:
    if visibility is ConfigVisibility.SHARED:
        return ConfigVisibility.PRIVATE
    return visibility
