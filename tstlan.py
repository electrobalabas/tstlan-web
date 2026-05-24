from enum import StrEnum
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class NetVarCType(StrEnum):
    U8 = "u8"
    I8 = "i8"
    U16 = "u16"
    I16 = "i16"
    U32 = "u32"
    I32 = "i32"
    F32 = "f32"
    F64 = "f64"


class NetVarMode(StrEnum):
    R = "r"
    W = "w"
    RW = "rw"


class NetVar:
    def __init__(
        self,
        name: str,
        ctype: NetVarCType,
        mode: NetVarMode,
        value: int | float = 0,
    ) -> None:
        self.name = name
        self.ctype = ctype
        self.mode = mode
        self.value: int | float = value


class WriteRequest(BaseModel):
    value: int | float


def create_app(var: NetVar | None = None) -> FastAPI:
    if var is None:
        var = NetVar("asdasdasd", NetVarCType.U32, NetVarMode.RW, value=5)
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
