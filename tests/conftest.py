from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.db import create_engine, create_sessionmaker, init_db


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    sessionmaker = create_sessionmaker(engine)
    async with sessionmaker() as db_session:
        yield db_session
    await engine.dispose()
