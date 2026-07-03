import logging
import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from tstlan.auth.models import Role, Session, User, utcnow
from tstlan.auth.passwords import hash_password, verify_password
from tstlan.logging_setup import get_service_logger, log_event

_TOKEN_BYTES = 32
logger = get_service_logger("auth")


async def create_user(
    db: AsyncSession, *, login: str, password: str, role: Role = Role.USER
) -> User:
    user = User(login=login, password_hash=hash_password(password), role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    log_event(
        logger,
        logging.INFO,
        "auth.user.created",
        user_id=user.id,
        login=user.login,
        role=user.role,
    )
    return user


async def list_users(db: AsyncSession) -> list[User]:
    result = await db.execute(
        select(User).where(User.is_active.is_(True)).order_by(User.login)
    )
    users = list(result.scalars().all())
    log_event(logger, logging.DEBUG, "auth.users.listed", count=len(users))
    return users


async def authenticate(db: AsyncSession, login: str, password: str) -> User | None:
    user = (
        await db.execute(select(User).where(User.login == login))
    ).scalar_one_or_none()
    if user is None:
        log_event(
            logger,
            logging.WARNING,
            "auth.login.rejected",
            login=login,
            reason="not_found",
        )
        return None
    if not user.is_active:
        log_event(
            logger,
            logging.WARNING,
            "auth.login.rejected",
            login=login,
            reason="inactive",
        )
        return None
    if not verify_password(user.password_hash, password):
        log_event(
            logger,
            logging.WARNING,
            "auth.login.rejected",
            login=login,
            user_id=user.id,
            reason="bad_password",
        )
        return None
    log_event(logger, logging.INFO, "auth.login.accepted", login=login, user_id=user.id)
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
    log_event(
        logger,
        logging.INFO,
        "auth.session.created",
        user_id=user.id,
        login=user.login,
        expires_at=session.expires_at.isoformat(),
    )
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
    if session is None:
        log_event(logger, logging.DEBUG, "auth.session.missing")
        return None
    if session.expires_at <= now:
        log_event(
            logger,
            logging.INFO,
            "auth.session.expired",
            user_id=session.user_id,
            expires_at=session.expires_at.isoformat(),
        )
        return None
    if now - (session.expires_at - ttl) >= refresh_after:
        session.expires_at = now + ttl
        await db.commit()
        log_event(
            logger,
            logging.DEBUG,
            "auth.session.refreshed",
            user_id=session.user_id,
            expires_at=session.expires_at.isoformat(),
        )
    return session


async def revoke_session(db: AsyncSession, token: str) -> None:
    session = await db.get(Session, token)
    if session is not None:
        user_id = session.user_id
        await db.delete(session)
        await db.commit()
        log_event(logger, logging.INFO, "auth.session.revoked", user_id=user_id)
