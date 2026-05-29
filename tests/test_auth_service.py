from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.passwords import verify_password
from tstlan.auth.service import (
    authenticate,
    create_session,
    create_user,
    lookup_session,
    revoke_session,
)

pytestmark = pytest.mark.anyio


async def test_create_user_stores_a_verifiable_hash(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    assert verify_password(user.password_hash, "pw")


async def test_authenticate_accepts_valid_credentials(session: AsyncSession) -> None:
    created = await create_user(session, login="alice", password="pw")
    assert await authenticate(session, "alice", "pw") is created


async def test_authenticate_rejects_wrong_password(session: AsyncSession) -> None:
    await create_user(session, login="alice", password="pw")
    assert await authenticate(session, "alice", "guess") is None


async def test_authenticate_rejects_unknown_login(session: AsyncSession) -> None:
    assert await authenticate(session, "ghost", "pw") is None


async def test_authenticate_rejects_inactive_user(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    user.is_active = False
    await session.commit()
    assert await authenticate(session, "alice", "pw") is None


async def test_lookup_returns_user_of_valid_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    token = (await create_session(session, user, ttl=timedelta(hours=1))).token
    assert await lookup_session(session, token) is user


async def test_lookup_rejects_expired_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    token = (await create_session(session, user, ttl=timedelta(seconds=-1))).token
    assert await lookup_session(session, token) is None


async def test_lookup_rejects_unknown_token(session: AsyncSession) -> None:
    assert await lookup_session(session, "missing") is None


async def test_revoke_invalidates_the_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    token = (await create_session(session, user, ttl=timedelta(hours=1))).token
    await revoke_session(session, token)
    assert await lookup_session(session, token) is None
