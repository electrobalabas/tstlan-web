import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from tstlan.config import Settings
from tstlan.db import create_engine, create_sessionmaker
from tstlan.devices.routes import register_exception_handlers
from tstlan.devices.routes import router as devices_router
from tstlan.devices.service import DeviceService, default_devices


def create_app(*, settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)
    shutdown_event = asyncio.Event()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            shutdown_event.set()
            await engine.dispose()

    app = FastAPI(title="TSTLAN web platform", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker
    app.state.devices = DeviceService(default_devices())
    app.state.shutdown_event = shutdown_event

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    app.include_router(devices_router)
    register_exception_handlers(app)

    return app
