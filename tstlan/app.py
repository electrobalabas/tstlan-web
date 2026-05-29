from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from tstlan.config import Settings
from tstlan.db import create_engine, create_sessionmaker


def create_app(*, settings: Settings | None = None) -> FastAPI:
    if settings is None:
        settings = Settings()

    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(title="TSTLAN web platform", lifespan=lifespan)
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    return app
