from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.models import Role
from tstlan.auth.service import (
    authenticate,
    create_session,
    create_user,
    lookup_session,
    revoke_session,
)

pytestmark = pytest.mark.anyio


async def test_create_user_hashes_password(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw", role=Role.ADMIN)
    assert user.id is not None
    assert user.role is Role.ADMIN
    assert user.password_hash != "pw"


async def test_authenticate_success(session: AsyncSession) -> None:
    await create_user(session, login="alice", password="pw")
    user = await authenticate(session, "alice", "pw")
    assert user is not None
    assert user.login == "alice"


async def test_authenticate_wrong_password(session: AsyncSession) -> None:
    await create_user(session, login="alice", password="pw")
    assert await authenticate(session, "alice", "nope") is None


async def test_authenticate_unknown_login(session: AsyncSession) -> None:
    assert await authenticate(session, "ghost", "pw") is None


async def test_authenticate_inactive_user(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    user.is_active = False
    await session.commit()
    assert await authenticate(session, "alice", "pw") is None


async def test_create_and_lookup_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    created = await create_session(session, user, ttl=timedelta(hours=1))
    found = await lookup_session(session, created.token)
    assert found is not None
    assert found.id == user.id


async def test_lookup_expired_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    created = await create_session(session, user, ttl=timedelta(seconds=-1))
    assert await lookup_session(session, created.token) is None


async def test_lookup_unknown_token(session: AsyncSession) -> None:
    assert await lookup_session(session, "nope") is None


async def test_revoke_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    created = await create_session(session, user, ttl=timedelta(hours=1))
    await revoke_session(session, created.token)
    assert await lookup_session(session, created.token) is None
