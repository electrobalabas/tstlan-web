from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Any

from fastapi import FastAPI

from tstlan.auth.middleware import AuthCsrfMiddleware
from tstlan.auth.routes import router as auth_router
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
    app.state.settings = settings

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

    return app
