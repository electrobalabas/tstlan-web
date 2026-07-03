import argparse
import asyncio
from collections.abc import Callable
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.models import User
from tstlan.auth.service import create_user
from tstlan.config import Settings, load_settings
from tstlan.db import create_engine, create_sessionmaker, run_migrations
from tstlan.logging_setup import get_logger
from tstlan.tools.seed_data import CONFIGS, USERS, SeedConfig

ClientFactory = Callable[[], httpx.Client]
logger = get_logger(__name__)


async def _insert_users(db: AsyncSession) -> None:
    for user in USERS:
        existing = (
            await db.execute(select(User).where(User.login == user.login))
        ).scalar_one_or_none()
        if existing is None:
            await create_user(
                db, login=user.login, password=user.password, role=user.role
            )
            logger.info("seed user created", extra={"login": user.login})


def seed_users(settings: Settings) -> None:
    async def run() -> None:
        engine = create_engine(settings.database_url)
        async with create_sessionmaker(engine)() as db:
            await _insert_users(db)
        await engine.dispose()

    asyncio.run(run())


class ApiClient:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def login(self, login: str, password: str) -> None:
        response = self._http.post(
            "/auth/login", json={"login": login, "password": password}
        )
        response.raise_for_status()
        self._http.headers["X-CSRF-Token"] = response.json()["csrf_token"]

    def create_config(self, config: SeedConfig) -> int:
        response = self._http.post(
            "/configs",
            json={
                "name": config.name,
                "device_type": config.device_type,
                "payload": config.payload,
                "visibility": config.visibility,
            },
        )
        response.raise_for_status()
        return response.json()["id"]

    def share(self, config_id: int, login: str, permission: str) -> None:
        response = self._http.post(
            f"/configs/{config_id}/shares",
            json={"login": login, "permission": permission},
        )
        response.raise_for_status()


def seed_configs(client_factory: ClientFactory, passwords: dict[str, str]) -> None:
    for config in CONFIGS:
        with client_factory() as http:
            api = ApiClient(http)
            api.login(config.owner, passwords[config.owner])
            config_id = api.create_config(config)
            logger.info(
                "seed config created",
                extra={"config_id": config_id, "owner": config.owner},
            )
            for grant in config.shares:
                api.share(config_id, grant.login, grant.permission)
                logger.info(
                    "seed config shared",
                    extra={
                        "config_id": config_id,
                        "grantee": grant.login,
                        "permission": grant.permission,
                    },
                )


def _http_factory(base_url: str, origin: str) -> ClientFactory:
    # каждый конфиг логинится своим владельцем -> свежий клиент с чистыми куками
    return lambda: httpx.Client(base_url=base_url, headers={"Origin": origin})


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tstlan-seed",
        description="наполнить запущенный сервер тестовыми данными",
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--config", type=Path, default=Path("config.toml"))
    parser.add_argument("--database-url", help="database URL, overrides config")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = load_settings(args.config)
    if args.database_url:
        settings = settings.model_copy(update={"database_url": args.database_url})
    run_migrations(settings.database_url)
    seed_users(settings)
    passwords = {user.login: user.password for user in USERS}
    seed_configs(_http_factory(args.base_url, settings.allowed_origins[0]), passwords)
    logger.info("seed completed", extra={"users": len(USERS), "configs": len(CONFIGS)})
    print(f"сид готов: {len(USERS)} пользователей, {len(CONFIGS)} конфигов")  # noqa: T201


if __name__ == "__main__":
    main()
