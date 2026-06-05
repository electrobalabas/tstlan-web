import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from tstlan.auth.models import Role, Session, User, utcnow
from tstlan.auth.passwords import hash_password, verify_password

_TOKEN_BYTES = 32


async def create_user(
    db: AsyncSession, *, login: str, password: str, role: Role = Role.USER
) -> User:
    user = User(login=login, password_hash=hash_password(password), role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.login)
    )
    return list(result.scalars().all())


async def authenticate(db: AsyncSession, login: str, password: str) -> User | None:
    user = (
        await db.execute(select(User).where(User.login == login))
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    if not verify_password(user.password_hash, password):
        return None
    return user


async def create_session(db: AsyncSession, user: User, *, ttl: timedelta) -> Session:
    session = Session(
        token=secrets.token_urlsafe(_TOKEN_BYTES),
        csrf_token=secrets.token_urlsafe(_TOKEN_BYTES),
        user_id=user.id,
        expires_at=utcnow() + ttl,
    )
    db.add(session)
    await db.commit()
    return session


async def resolve_session(
    db: AsyncSession, token: str, *, ttl: timedelta, refresh_after: timedelta
) -> Session | None:
    session = (
        await db.execute(
            select(Session)
            .where(Session.token == token)
            .options(joinedload(Session.user))
        )
    ).scalar_one_or_none()
    now = utcnow()
    if session is None or session.expires_at <= now:
        return None
    if now - (session.expires_at - ttl) >= refresh_after:
        session.expires_at = now + ttl
        await db.commit()
    return session


async def revoke_session(db: AsyncSession, token: str) -> None:
    session = await db.get(Session, token)
    if session is not None:
        await db.delete(session)
        await db.commit()
