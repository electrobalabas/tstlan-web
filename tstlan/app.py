from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tstlan.config import Settings
from tstlan.db import create_engine, create_sessionmaker, init_db
from tstlan.models import NetVar, NetVarCType, NetVarMode


class WriteRequest(BaseModel):
    value: int | float


def create_app(
    var: NetVar | None = None, *, settings: Settings | None = None
) -> FastAPI:
    if settings is None:
        settings = Settings()
    if var is None:
        var = NetVar("voltage", NetVarCType.U32, NetVarMode.RW, value=5)

    engine = create_engine(settings.database_url)
    sessionmaker = create_sessionmaker(engine)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        await init_db(engine)
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

    @app.get("/var")
    def read_var() -> dict[str, Any]:
        if var.mode is NetVarMode.W:
            raise HTTPException(status_code=403, detail="variable is write-only")
        return {
            "name": var.name,
            "ctype": var.ctype,
            "mode": var.mode,
            "value": var.value,
        }

    @app.post("/var")
    def write_var(payload: WriteRequest) -> dict[str, Any]:
        if var.mode is NetVarMode.R:
            raise HTTPException(status_code=403, detail="variable is read-only")
        var.value = payload.value
        return {"value": var.value}

    return app
