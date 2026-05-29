import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.anyio


async def test_init_db_and_session_query(session: AsyncSession) -> None:
    result = await session.execute(text("SELECT 1"))
    assert result.scalar_one() == 1
