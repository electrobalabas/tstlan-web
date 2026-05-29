from fastapi.testclient import TestClient

from tstlan.app import create_app
from tstlan.config import Settings
from tstlan.models import NetVar, NetVarCType, NetVarMode


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_boots_with_db_lifespan() -> None:
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:")
    with TestClient(create_app(settings=settings)) as client:
        assert client.get("/health").json() == {"status": "ok"}


def test_read_var_returns_state() -> None:
    var = NetVar("voltage", NetVarCType.U32, NetVarMode.RW, value=5)
    client = TestClient(create_app(var))
    response = client.get("/var")
    assert response.status_code == 200
    assert response.json() == {
        "name": "voltage",
        "ctype": "u32",
        "mode": "rw",
        "value": 5,
    }


def test_write_var_updates_value() -> None:
    client = TestClient(create_app())
    response = client.post("/var", json={"value": 42})
    assert response.status_code == 200
    assert response.json() == {"value": 42}
    assert client.get("/var").json()["value"] == 42


def test_write_readonly_var_forbidden() -> None:
    var = NetVar("ro", NetVarCType.U16, NetVarMode.R, value=1)
    client = TestClient(create_app(var))
    response = client.post("/var", json={"value": 9})
    assert response.status_code == 403


def test_read_writeonly_var_forbidden() -> None:
    var = NetVar("wo", NetVarCType.U16, NetVarMode.W, value=1)
    client = TestClient(create_app(var))
    response = client.get("/var")
    assert response.status_code == 403


def test_write_float_value() -> None:
    var = NetVar("f", NetVarCType.F32, NetVarMode.RW, value=0.0)
    client = TestClient(create_app(var))
    response = client.post("/var", json={"value": 1.5})
    assert response.status_code == 200
    assert response.json() == {"value": 1.5}
