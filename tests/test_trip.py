from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.models import Role
from tstlan.auth.service import create_user
from tstlan.configs.models import ConfigVisibility, DeviceConfig
from tstlan.configs.schemas import ConfigCreate, ConfigPayload
from tstlan.configs.service import create_config
from tstlan.trip import (
    ConfigSnapshot,
    TripAction,
    apply_import,
    build_import_plan,
    read_bundle,
    snapshot_device_configs,
    write_export_bundle,
    write_pack_bundle,
)

pytestmark = pytest.mark.anyio


def _snapshot(
    sync_id: str,
    *,
    name: str = "cfg",
    owner_login: str = "dev",
    payload: dict | None = None,
) -> ConfigSnapshot:
    return ConfigSnapshot(
        sync_id=sync_id,
        owner_login=owner_login,
        name=name,
        device_type="multimeter",
        payload=payload or {"variables": []},
        visibility=ConfigVisibility.PRIVATE,
    )


async def _user(session: AsyncSession, login: str = "dev"):
    return await create_user(session, login=login, password="pw", role=Role.DEV)


async def _config(
    session: AsyncSession,
    *,
    sync_id: str = "cfg-1",
    name: str = "cfg",
    payload: ConfigPayload | None = None,
) -> DeviceConfig:
    user = await _user(session)
    config = await create_config(
        session,
        user,
        ConfigCreate(
            name=name,
            device_type="multimeter",
            payload=payload or ConfigPayload(),
        ),
    )
    config.sync_id = sync_id
    await session.commit()
    return config


def test_build_import_plan_detects_update_and_conflict() -> None:
    base = [_snapshot("cfg-1", name="base"), _snapshot("cfg-2", name="base")]
    field = [_snapshot("cfg-1", name="field"), _snapshot("cfg-2", name="field")]
    prod = [_snapshot("cfg-1", name="base"), _snapshot("cfg-2", name="prod")]

    plan = build_import_plan(base, field, prod)

    assert [(item.sync_id, item.action) for item in plan.items] == [
        ("cfg-1", TripAction.UPDATE),
        ("cfg-2", TripAction.CONFLICT),
    ]
    assert plan.updates == 1
    assert plan.conflicts == 1


def test_export_and_pack_bundle_round_trip(tmp_path: Path) -> None:
    export_path = tmp_path / "before.tslan-bundle"
    pack_path = tmp_path / "after.tslan-bundle"

    write_export_bundle(export_path, [_snapshot("cfg-1", name="base")])
    write_pack_bundle(
        pack_path,
        base_bundle=export_path,
        field_configs=[_snapshot("cfg-1", name="field")],
    )

    bundle = read_bundle(pack_path)
    assert [item.name for item in bundle.base] == ["base"]
    assert bundle.field is not None
    assert [item.name for item in bundle.field] == ["field"]


async def test_apply_import_updates_when_prod_unchanged(
    session: AsyncSession, tmp_path: Path
) -> None:
    await _config(session, sync_id="cfg-1", name="base")
    bundle_path = tmp_path / "after.tslan-bundle"
    write_pack_bundle(
        bundle_path,
        base_bundle=_export(tmp_path, [_snapshot("cfg-1", name="base")]),
        field_configs=[_snapshot("cfg-1", name="field")],
    )

    plan = await apply_import(session, bundle_path)

    config = await _one_config(session)
    assert plan.updates == 1
    assert config.name == "field"


async def test_apply_import_copies_conflict_by_default(
    session: AsyncSession, tmp_path: Path
) -> None:
    await _config(session, sync_id="cfg-1", name="prod")
    bundle_path = tmp_path / "after.tslan-bundle"
    write_pack_bundle(
        bundle_path,
        base_bundle=_export(tmp_path, [_snapshot("cfg-1", name="base")]),
        field_configs=[_snapshot("cfg-1", name="field")],
    )

    plan = await apply_import(session, bundle_path)

    names = await _config_names(session)
    assert plan.conflicts == 1
    assert names == ["field (field copy)", "prod"]


async def test_snapshot_normalizes_shared_visibility(session: AsyncSession) -> None:
    config = await _config(session, sync_id="cfg-1", name="base")
    config.visibility = ConfigVisibility.SHARED
    await session.commit()

    snapshot = await snapshot_device_configs(session)

    assert snapshot[0].visibility is ConfigVisibility.PRIVATE


def _export(tmp_path: Path, base: list[ConfigSnapshot]) -> Path:
    path = tmp_path / "before.tslan-bundle"
    write_export_bundle(path, base)
    return path


async def _one_config(session: AsyncSession) -> DeviceConfig:
    return (await session.execute(select(DeviceConfig))).scalar_one()


async def _config_names(session: AsyncSession) -> list[str]:
    rows = (
        await session.execute(select(DeviceConfig.name).order_by(DeviceConfig.name))
    ).all()
    return [row[0] for row in rows]
