import argparse
from pathlib import Path

import uvicorn

from tstlan.app import create_app
from tstlan.config import load_settings
from tstlan.logging_setup import init_logging

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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = load_settings(args.config)
    overrides = {
        key: value
        for key, value in (
            ("bind_host", args.host),
            ("bind_port", args.port),
            ("log_level", args.log_level),
        )
        if value is not None
    }
    if overrides:
        settings = settings.model_copy(update=overrides)
    init_logging(settings.log_level)
    uvicorn.run(create_app(), host=settings.bind_host, port=settings.bind_port)


if __name__ == "__main__":
    main()
