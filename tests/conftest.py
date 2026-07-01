import asyncio
from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.app import create_app
from tstlan.auth.models import Role, User
from tstlan.auth.routes import current_user
from tstlan.auth.service import create_user
from tstlan.db import create_engine, create_sessionmaker, init_db
from tstlan.devices.models import Device, DeviceStatus
from tstlan.devices.routes import get_service
from tstlan.devices.service import DeviceService
from tstlan.models import NetVar, NetVarCType, NetVarMode

TEST_ORIGIN = "http://app.test"
FOREIGN_ORIGIN = "http://evil.test"
USER_PASSWORD = "pw"

UserSeed = tuple[str, Role]
SqliteUrlFactory = Callable[[str], str]
SeedUsers = Callable[[str, Sequence[UserSeed]], None]


class AuthenticatedClient:
    """Залогиненный клиент с CSRF-токеном для безопасных мутаций."""

    def __init__(self, app: Any, login: str, *, password: str = USER_PASSWORD) -> None:
        self.http = TestClient(app)
        body = self.http.post(
            "/auth/login",
            json={"login": login, "password": password},
            headers={"Origin": TEST_ORIGIN},
        ).json()
        self._headers = {"Origin": TEST_ORIGIN, "X-CSRF-Token": body["csrf_token"]}

    def get(self, url: str) -> httpx.Response:
        return self.http.get(url)

    def post(self, url: str, json: dict[str, Any]) -> httpx.Response:
        return self.http.post(url, json=json, headers=self._headers)

    def put(self, url: str, json: dict[str, Any]) -> httpx.Response:
        return self.http.put(url, json=json, headers=self._headers)

    def delete(self, url: str) -> httpx.Response:
        return self.http.delete(url, headers=self._headers)


def _force_user(app: FastAPI, role: Role) -> None:
    user = User(id=1, login="tester", password_hash="", role=role, is_active=True)
    app.dependency_overrides[current_user] = lambda: user


async def _seed_users(database_url: str, users: Sequence[UserSeed]) -> None:
    engine = create_engine(database_url)
    await init_db(engine)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as db:
        for login, role in users:
            await create_user(db, login=login, password=USER_PASSWORD, role=role)
    await engine.dispose()


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def sqlite_url(tmp_path: Path) -> SqliteUrlFactory:
    def build(name: str) -> str:
        return f"sqlite+aiosqlite:///{tmp_path / name}"

    return build


@pytest.fixture
def seed_users() -> SeedUsers:
    def seed(database_url: str, users: Sequence[UserSeed]) -> None:
        asyncio.run(_seed_users(database_url, users))

    return seed


@pytest.fixture
def authenticated_client() -> type[AuthenticatedClient]:
    return AuthenticatedClient


@pytest.fixture
def allowed_origin() -> str:
    return TEST_ORIGIN


@pytest.fixture
def foreign_origin() -> str:
    return FOREIGN_ORIGIN


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as db_session:
        yield db_session
    await engine.dispose()


@pytest.fixture
def devices_service() -> DeviceService:
    return DeviceService.from_devices(
        [
            Device(
                id="dev",
                name="Прибор",
                type="Эмулятор",
                enabled=True,
                status=DeviceStatus.OK,
                variables=[
                    NetVar("voltage", NetVarCType.F32, NetVarMode.RW),
                    NetVar("level", NetVarCType.U8, NetVarMode.RW, value=1),
                    NetVar("counter", NetVarCType.U32, NetVarMode.R, value=7),
                    NetVar("reset", NetVarCType.U8, NetVarMode.W),
                ],
            ),
            Device(
                id="spare",
                name="Резерв",
                type="Эмулятор",
                enabled=False,
                status=DeviceStatus.OFFLINE,
                variables=[NetVar("setpoint", NetVarCType.F32, NetVarMode.RW)],
            ),
        ]
    )


@pytest.fixture
def devices_app(devices_service: DeviceService) -> Iterator[FastAPI]:
    app = create_app()
    app.dependency_overrides[get_service] = lambda: devices_service
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def devices_client(devices_app: FastAPI) -> TestClient:
    _force_user(devices_app, Role.DEV)
    return TestClient(devices_app)


@pytest.fixture
def login_as() -> Callable[[FastAPI, Role], None]:
    return _force_user
