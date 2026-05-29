from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth import Role, Session, User

pytestmark = pytest.mark.anyio


async def test_user_defaults(session: AsyncSession) -> None:
    user = User(login="alice", password_hash="hash")
    session.add(user)
    await session.commit()
    await session.refresh(user)

    assert user.id is not None
    assert user.role is Role.USER
    assert user.is_active is True
    assert user.created_at is not None


async def test_role_roundtrips_to_enum(session: AsyncSession) -> None:
    session.add(User(login="root", password_hash="hash", role=Role.ADMIN))
    await session.commit()

    stored = (
        await session.execute(select(User).where(User.login == "root"))
    ).scalar_one()
    assert stored.role is Role.ADMIN


async def test_login_is_unique(session: AsyncSession) -> None:
    session.add(User(login="dup", password_hash="a"))
    await session.commit()

    session.add(User(login="dup", password_hash="b"))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_deleting_user_cascades_to_sessions(session: AsyncSession) -> None:
    user = User(login="carol", password_hash="hash")
    session.add(user)
    await session.commit()
    session.add(
        Session(
            token="tok-1",
            user_id=user.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(hours=1),
        )
    )
    await session.commit()

    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()

    remaining = (await session.execute(select(Session))).first()
    assert remaining is None
