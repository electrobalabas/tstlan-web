import pytest
from sqlalchemy import text

from tstlan.db import create_engine, create_sessionmaker, init_db

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


async def test_init_db_and_session_query() -> None:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as session:
        result = await session.execute(text("SELECT 1"))
        assert result.scalar_one() == 1
    await engine.dispose()
