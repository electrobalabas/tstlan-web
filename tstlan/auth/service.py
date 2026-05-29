import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
        user_id=user.id,
        expires_at=utcnow() + ttl,
    )
    db.add(session)
    await db.commit()
    return session


async def lookup_session(db: AsyncSession, token: str) -> User | None:
    session = await db.get(Session, token)
    if session is None or session.expires_at <= utcnow():
        return None
    return await db.get(User, session.user_id)


async def revoke_session(db: AsyncSession, token: str) -> None:
    session = await db.get(Session, token)
    if session is not None:
        await db.delete(session)
        await db.commit()
