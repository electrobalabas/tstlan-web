from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from tstlan.config import load_settings
from tstlan.logging_setup import init_logging
from tstlan.models import NetVar, NetVarCType, NetVarMode

settings = load_settings(Path("config.toml"))
init_logging(settings.log_level)


class WriteRequest(BaseModel):
    value: int | float


def create_app(var: NetVar | None = None) -> FastAPI:
    if var is None:
        var = NetVar("voltage", NetVarCType.U32, NetVarMode.RW, value=5)
    app = FastAPI(title="TSTLAN web platform")

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


app = create_app()
