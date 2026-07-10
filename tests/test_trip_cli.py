from pathlib import Path

from tstlan.__main__ import main
from tstlan.app import create_app
from tstlan.auth.models import Role
from tstlan.config import Settings
from tstlan.configs.models import DeviceConfig


def test_trip_cli_export_pack_and_dry_run(
    sqlite_url, seed_users, authenticated_client, capsys, tmp_path: Path
) -> None:
    db_url = sqlite_url("trip-cli.db")
    seed_users(db_url, [("dev", Role.DEV)])
    app = create_app(settings=_settings(db_url))
    dev = authenticated_client(app, "dev")
    dev.post(
        "/configs",
        {
            "name": "base",
            "device_type": "multimeter",
            "payload": {"variables": []},
        },
    ).json()

    export_path = tmp_path / "before.tslan-bundle"
    pack_path = tmp_path / "after.tslan-bundle"
    main(["trip", "export", "--database-url", db_url, str(export_path)])

    main(
        [
            "trip",
            "pack",
            "--database-url",
            db_url,
            str(export_path),
            str(pack_path),
        ]
    )
    main(["trip", "import", "--database-url", db_url, "--dry-run", str(pack_path)])

    output = capsys.readouterr().out
    assert "exported 1 device configs" in output
    assert "packed 1 device configs" in output
    assert "device configs: 0 create, 0 update, 1 skip, 0 conflict" in output


def test_trip_cli_import_applies_update(
    sqlite_url, seed_users, authenticated_client, tmp_path: Path
) -> None:
    prod_url = sqlite_url("trip-prod.db")
    field_url = sqlite_url("trip-field.db")
    seed_users(prod_url, [("dev", Role.DEV)])
    seed_users(field_url, [("dev", Role.DEV)])
    prod_app = create_app(settings=_settings(prod_url))
    field_app = create_app(settings=_settings(field_url))
    prod_dev = authenticated_client(prod_app, "dev")
    field_dev = authenticated_client(field_app, "dev")
    prod_created = prod_dev.post(
        "/configs",
        {"name": "base", "device_type": "multimeter", "payload": {"variables": []}},
    ).json()
    field_created = field_dev.post(
        "/configs",
        {"name": "base", "device_type": "multimeter", "payload": {"variables": []}},
    ).json()

    _set_sync_id(prod_url, prod_created["id"], "cfg-1")
    _set_sync_id(field_url, field_created["id"], "cfg-1")
    export_path = tmp_path / "before.tslan-bundle"
    pack_path = tmp_path / "after.tslan-bundle"
    main(["trip", "export", "--database-url", prod_url, str(export_path)])
    field_dev.put(f"/configs/{field_created['id']}", {"name": "field"})
    main(
        ["trip", "pack", "--database-url", field_url, str(export_path), str(pack_path)]
    )

    main(["trip", "import", "--database-url", prod_url, str(pack_path)])

    assert prod_dev.get(f"/configs/{prod_created['id']}").json()["name"] == "field"


def _set_sync_id(database_url: str, config_id: int, sync_id: str) -> None:
    from sqlalchemy import create_engine as create_sync_engine
    from sqlalchemy import update

    sync_url = database_url.replace("+aiosqlite", "")
    engine = create_sync_engine(sync_url)
    try:
        with engine.begin() as conn:
            conn.execute(
                update(DeviceConfig)
                .where(DeviceConfig.id == config_id)
                .values(sync_id=sync_id)
            )
    finally:
        engine.dispose()


def _settings(database_url: str) -> Settings:
    return Settings(database_url=database_url, allowed_origins=["http://app.test"])
