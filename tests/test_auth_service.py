from datetime import timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.passwords import verify_password
from tstlan.auth.service import (
    authenticate,
    create_session,
    create_user,
    resolve_session,
    revoke_session,
)

pytestmark = pytest.mark.anyio

_TTL = timedelta(hours=720)
_REFRESH = timedelta(hours=24)


async def test_create_user_stores_a_verifiable_hash(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    assert verify_password(user.password_hash, "pw")


async def test_create_session_mints_a_csrf_token(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    created = await create_session(session, user, ttl=timedelta(hours=1))
    assert created.csrf_token


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


async def test_resolve_returns_session_of_valid_token(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    token = (await create_session(session, user, ttl=_TTL)).token
    resolved = await resolve_session(session, token, ttl=_TTL, refresh_after=_REFRESH)
    assert resolved is not None and resolved.user is user


async def test_resolve_rejects_expired_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    token = (await create_session(session, user, ttl=timedelta(seconds=-1))).token
    assert (
        await resolve_session(session, token, ttl=_TTL, refresh_after=_REFRESH) is None
    )


async def test_resolve_rejects_unknown_token(session: AsyncSession) -> None:
    assert (
        await resolve_session(session, "missing", ttl=_TTL, refresh_after=_REFRESH)
        is None
    )


async def test_resolve_slides_expiry_past_refresh_window(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    created = await create_session(session, user, ttl=timedelta(hours=1))
    before = created.expires_at
    resolved = await resolve_session(
        session, created.token, ttl=_TTL, refresh_after=timedelta(0)
    )
    assert resolved is not None and resolved.expires_at > before


async def test_resolve_keeps_expiry_within_refresh_window(
    session: AsyncSession,
) -> None:
    user = await create_user(session, login="alice", password="pw")
    created = await create_session(session, user, ttl=_TTL)
    before = created.expires_at
    resolved = await resolve_session(
        session, created.token, ttl=_TTL, refresh_after=_REFRESH
    )
    assert resolved is not None and resolved.expires_at == before


async def test_revoke_invalidates_the_session(session: AsyncSession) -> None:
    user = await create_user(session, login="alice", password="pw")
    token = (await create_session(session, user, ttl=_TTL)).token
    await revoke_session(session, token)
    assert (
        await resolve_session(session, token, ttl=_TTL, refresh_after=_REFRESH) is None
    )
