from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.config import Settings


def test_health_reports_ok() -> None:
    client = TestClient(create_app())
    assert client.get("/health").json() == {"status": "ok"}


def test_app_boots_with_db_lifespan() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    with TestClient(create_app(settings=settings)) as client:
        assert client.get("/health").json() == {"status": "ok"}
