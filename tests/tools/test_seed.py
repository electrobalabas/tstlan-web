from pathlib import Path

from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.config import Settings
from tstlan.configs.schemas import ConfigCreate
from tstlan.db import run_migrations
from tstlan.tools.seed import seed_configs, seed_users
from tstlan.tools.seed_data import CONFIGS, USERS


def test_seed_configs_are_valid_payloads() -> None:
    for config in CONFIGS:
        ConfigCreate.model_validate(
            {
                "name": config.name,
                "device_type": config.device_type,
                "payload": config.payload,
                "visibility": config.visibility,
            }
        )


def _seeded_app(tmp_path: Path) -> tuple[TestClient, str]:
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'seed.db'}"
    run_migrations(db_url)
    settings = Settings(database_url=db_url)
    app = create_app(settings=settings)
    origin = settings.allowed_origins[0]
    seed_users(settings)
    seed_configs(
        lambda: TestClient(app, headers={"Origin": origin}),
        {user.login: user.password for user in USERS},
    )
    return TestClient(app, headers={"Origin": origin}), origin


def _login(client: TestClient, login: str, password: str) -> None:
    client.post("/auth/login", json={"login": login, "password": password})


def test_seed_creates_configs_with_visibility(tmp_path: Path) -> None:
    client, _ = _seeded_app(tmp_path)
    _login(client, "admin", "admin123")
    configs = client.get("/configs").json()
    assert {c["name"]: c["visibility"] for c in configs} == {
        "Стенд мультиметра": "public",
        "Калибратор линии": "shared",
        "Личный термостат": "private",
    }


def test_seed_applies_shares(tmp_path: Path) -> None:
    client, _ = _seeded_app(tmp_path)
    _login(client, "operator", "operator123")
    calibrator = next(
        c for c in client.get("/configs").json() if c["name"] == "Калибратор линии"
    )
    detail = client.get(f"/configs/{calibrator['id']}").json()
    assert {(s["login"], s["permission"]) for s in detail["shares"]} == {
        ("viewer", "read"),
        ("engineer", "write"),
    }
