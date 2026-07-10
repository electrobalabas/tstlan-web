import asyncio
import argparse
from pathlib import Path

import uvicorn

from tstlan.app import create_app
from tstlan.config import load_settings
from tstlan.db import create_engine, create_sessionmaker
from tstlan.logging_setup import init_logging
from tstlan.trip import (
    ImportPlan,
    apply_import,
    plan_import,
    snapshot_device_configs,
    write_export_bundle,
    write_pack_bundle,
)

DEFAULT_CONFIG_PATH = Path("config.toml")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tstlan", description="TSTLAN web platform server"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="path to TOML config (default: config.toml)",
    )
    parser.add_argument("--host", help="bind host, overrides config")
    parser.add_argument("--port", type=int, help="bind port, overrides config")
    parser.add_argument("--log-level", help="log level, overrides config")
    parser.add_argument("--database-url", help="database URL, overrides config")
    trip = parser.add_subparsers(dest="command")
    trip_parser = trip.add_parser("trip", help="portable trip bundle commands")
    trip_sub = trip_parser.add_subparsers(dest="trip_command", required=True)

    export = trip_sub.add_parser("export", help="write base snapshot before a trip")
    _add_db_args(export)
    export.add_argument("output", type=Path, help="output .tslan-bundle archive")

    pack = trip_sub.add_parser("pack", help="pack field snapshot after a trip")
    _add_db_args(pack)
    pack.add_argument("base_bundle", type=Path, help="bundle produced by trip export")
    pack.add_argument("output", type=Path, help="output .tslan-bundle archive")

    import_parser = trip_sub.add_parser("import", help="preview or apply a trip bundle")
    _add_db_args(import_parser)
    import_parser.add_argument("bundle", type=Path, help="bundle produced by trip pack")
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned changes without applying them",
    )
    import_parser.add_argument(
        "--conflict",
        choices=("copy", "server", "field"),
        default="copy",
        help="conflict policy for apply mode (default: copy)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "trip":
        asyncio.run(_run_trip(args))
        return

    settings = load_settings(args.config)
    overrides = {
        key: value
        for key, value in (
            ("bind_host", args.host),
            ("bind_port", args.port),
            ("log_level", args.log_level),
            ("database_url", args.database_url),
        )
        if value is not None
    }
    if overrides:
        settings = settings.model_copy(update=overrides)
    init_logging(settings.log_level)
    uvicorn.run(
        create_app(settings=settings),
        host=settings.bind_host,
        port=settings.bind_port,
    )


def _add_db_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="path to TOML config (default: config.toml)",
    )
    parser.add_argument("--database-url", help="database URL, overrides config")


async def _run_trip(args: argparse.Namespace) -> None:
    settings = load_settings(args.config)
    if args.database_url is not None:
        settings = settings.model_copy(update={"database_url": args.database_url})
    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)
    try:
        async with sessionmaker() as db:
            if args.trip_command == "export":
                snapshot = await snapshot_device_configs(db)
                write_export_bundle(args.output, snapshot)
                print(f"exported {len(snapshot)} device configs to {args.output}")
            elif args.trip_command == "pack":
                snapshot = await snapshot_device_configs(db)
                write_pack_bundle(
                    args.output,
                    base_bundle=args.base_bundle,
                    field_configs=snapshot,
                )
                print(f"packed {len(snapshot)} device configs to {args.output}")
            elif args.trip_command == "import":
                if args.dry_run:
                    plan = await plan_import(db, args.bundle)
                    _print_plan(plan)
                else:
                    plan = await apply_import(
                        db,
                        args.bundle,
                        conflict_policy=args.conflict,
                    )
                    _print_plan(plan)
                    print(f"applied bundle {args.bundle}")
            else:
                raise SystemExit(f"unknown trip command: {args.trip_command}")
    finally:
        await engine.dispose()


def _print_plan(plan: ImportPlan) -> None:
    print(
        "device configs: "
        f"{plan.creates} create, {plan.updates} update, "
        f"{plan.skips} skip, {plan.conflicts} conflict"
    )
    for item in plan.items:
        detail = ", ".join(item.details)
        if item.conflict_fields:
            detail = f"{detail}; conflicts: {', '.join(item.conflict_fields)}"
        print(f"- {item.action.value}: {item.name} [{item.sync_id}] {detail}")


if __name__ == "__main__":
    main()
