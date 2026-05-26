import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    bind_host: str = "127.0.0.1"
    bind_port: int = 8000
    log_level: str = "INFO"


def load_settings(path: Path | None = None) -> Settings:
    if path is None or not path.exists():
        return Settings()
    with path.open("rb") as f:
        data = tomllib.load(f)
    return Settings.model_validate(data)
