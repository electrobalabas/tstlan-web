import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.models import Role, User
from tstlan.auth.service import create_user
from tstlan.config import Settings, load_settings
from tstlan.db import create_engine, create_sessionmaker, run_migrations


async def add_admin(db: AsyncSession, login: str, password: str) -> User:
    existing = (
        await db.execute(select(User).where(User.login == login))
    ).scalar_one_or_none()
    if existing is not None:
        raise SystemExit(f"пользователь {login!r} уже существует")
    return await create_user(db, login=login, password=password, role=Role.ADMIN)


async def _add_admin(settings: Settings, login: str, password: str) -> None:
    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as db:
        await add_admin(db, login, password)
    await engine.dispose()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tstlan-create-admin",
        description="создать локального администратора (bootstrap первого входа)",
    )
    parser.add_argument("--login", required=True, help="логин администратора")
    parser.add_argument("--password", required=True, help="пароль администратора")
    parser.add_argument(
        "--config", type=Path, default=Path("config.toml"), help="путь к TOML-конфигу"
    )
    parser.add_argument("--database-url", help="database URL, overrides config")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = load_settings(args.config)
    if args.database_url:
        settings = settings.model_copy(update={"database_url": args.database_url})
    run_migrations(settings.database_url)
    asyncio.run(_add_admin(settings, args.login, args.password))
    print(f"администратор {args.login!r} создан")


if __name__ == "__main__":
    main()
