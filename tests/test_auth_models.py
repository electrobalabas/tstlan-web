from datetime import timedelta

import pytest
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.models import Role, Session, User, utcnow

pytestmark = pytest.mark.anyio


async def test_new_user_defaults_to_active_regular_role(session: AsyncSession) -> None:
    user = User(login="alice", password_hash="hash")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    assert {"role": user.role, "is_active": user.is_active} == {
        "role": Role.USER,
        "is_active": True,
    }


async def test_explicit_role_survives_roundtrip(session: AsyncSession) -> None:
    session.add(User(login="root", password_hash="hash", role=Role.ADMIN))
    await session.commit()
    stored = (
        await session.execute(select(User).where(User.login == "root"))
    ).scalar_one()
    assert stored.role is Role.ADMIN


async def test_duplicate_login_is_rejected(session: AsyncSession) -> None:
    session.add(User(login="dup", password_hash="a"))
    await session.commit()
    session.add(User(login="dup", password_hash="b"))
    with pytest.raises(IntegrityError):
        await session.commit()


async def test_deleting_user_deletes_their_sessions(session: AsyncSession) -> None:
    user = User(login="carol", password_hash="hash")
    session.add(user)
    await session.commit()
    session.add(
        Session(token="tok", user_id=user.id, expires_at=utcnow() + timedelta(hours=1))
    )
    await session.commit()

    await session.execute(delete(User).where(User.id == user.id))
    await session.commit()
    assert (await session.execute(select(Session))).first() is None
