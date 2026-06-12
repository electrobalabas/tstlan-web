from collections.abc import AsyncIterator, Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.app import create_app
from tstlan.auth.models import Role, User
from tstlan.auth.routes import current_user
from tstlan.db import create_engine, create_sessionmaker, init_db
from tstlan.devices.models import Device, DeviceStatus
from tstlan.devices.routes import get_service
from tstlan.devices.service import DeviceService
from tstlan.models import NetVar, NetVarCType, NetVarMode


def _force_user(app: FastAPI, role: Role) -> None:
    user = User(id=1, login="tester", password_hash="", role=role, is_active=True)
    app.dependency_overrides[current_user] = lambda: user


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


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
