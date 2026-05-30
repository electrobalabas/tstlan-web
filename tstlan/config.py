import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    log_level: str = "INFO"
    database_url: str = "sqlite+aiosqlite:///./tstlan.db"
    session_ttl_hours: int = 720
    session_refresh_hours: int = 24
    cookie_secure: bool = False
    allowed_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def load_settings(path: Path | None = None) -> Settings:
    if path is None or not path.exists():
        return Settings()
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Settings.model_validate(data)
