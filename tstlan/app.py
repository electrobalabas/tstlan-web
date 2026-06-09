import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

from fastapi import FastAPI

from tstlan.auth.middleware import AuthCsrfMiddleware
from tstlan.auth.routes import router as auth_router
from tstlan.auth.routes import users_router
from tstlan.config import Settings
from tstlan.configs.routes import (
    register_exception_handlers as register_config_handlers,
)
from tstlan.configs.routes import router as configs_router
from tstlan.db import create_engine, create_sessionmaker
from tstlan.devices.net.client import LazySocketUnidriverIO
from tstlan.devices.routes import register_exception_handlers
from tstlan.devices.routes import router as devices_router
from tstlan.devices.runtime import attach_device, bind_device
from tstlan.devices.device_profile import device_from_profile, load_profile
from tstlan.devices.service import DeviceService
from tstlan.devices.simulation import SimulationEngine, default_simulated_devices
from tstlan.devices.unidriver import InMemoryUnidriverIO

# один процесс-прибор держит один прибор за хэндлом 1 (контракт шва, см. devsim)
_DEVICE_HANDLE = 1


def _build_devices(settings: Settings) -> tuple[DeviceService, SimulationEngine | None]:
    if settings.devices:
        runtimes = [
            attach_device(
                LazySocketUnidriverIO(endpoint.host, endpoint.port),
                device_from_profile(load_profile(endpoint.profile), endpoint.id),
                _DEVICE_HANDLE,
            )
            for endpoint in settings.devices
        ]
        return DeviceService(runtimes), None
    io = InMemoryUnidriverIO()
    catalog = default_simulated_devices()
    runtimes = [bind_device(io, item.device, item.handle) for item in catalog]
    return DeviceService(runtimes), SimulationEngine(io, catalog)


def create_app(*, settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)
    shutdown_event = asyncio.Event()
    devices, simulation = _build_devices(settings)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        task = (
            asyncio.create_task(simulation.run(shutdown_event))
            if simulation is not None
            else None
        )
        try:
            yield
        finally:
            shutdown_event.set()
            if task is not None:
                await task
            await engine.dispose()

    app = FastAPI(title="TSTLAN web platform", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.settings = settings
    app.state.devices = devices
    app.state.simulation = simulation
    app.state.shutdown_event = shutdown_event

    app.add_middleware(
        AuthCsrfMiddleware,
        sessionmaker=sessionmaker,
        ttl=timedelta(hours=settings.session_ttl_hours),
        refresh_after=timedelta(hours=settings.session_refresh_hours),
        allowed_origins=settings.allowed_origins,
        cookie_secure=settings.cookie_secure,
    )

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(devices_router)
    app.include_router(configs_router)
    register_exception_handlers(app)
    register_config_handlers(app)

    return app
