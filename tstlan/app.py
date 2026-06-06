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
from tstlan.devices.routes import register_exception_handlers
from tstlan.devices.routes import router as devices_router
from tstlan.devices.runtime import bind_device
from tstlan.devices.service import DeviceService
from tstlan.devices.simulation import SimulationEngine, default_simulated_devices
from tstlan.devices.unidriver import InMemoryUnidriverIO


def create_app(*, settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)
    shutdown_event = asyncio.Event()
    io = InMemoryUnidriverIO()
    catalog = default_simulated_devices()
    runtimes = [bind_device(io, item.device, item.handle) for item in catalog]
    simulation = SimulationEngine(io, catalog)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        simulation_task = asyncio.create_task(simulation.run(shutdown_event))
        try:
            yield
        finally:
            shutdown_event.set()
            await simulation_task
            await engine.dispose()

    app = FastAPI(title="TSTLAN web platform", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.settings = settings
    app.state.devices = DeviceService(runtimes)
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
