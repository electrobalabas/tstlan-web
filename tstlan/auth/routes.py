from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.middleware import (
    SESSION_COOKIE,
    clear_session_cookie,
    set_session_cookie,
)
from tstlan.auth.models import Role, User
from tstlan.auth.service import (
    authenticate,
    create_session,
    list_users,
    revoke_session,
)
from tstlan.config import Settings

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(tags=["users"])


class LoginRequest(BaseModel):
    login: str
    password: str


class UserSummary(BaseModel):
    login: str
    role: Role


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as db:
        yield db


def current_user(request: Request) -> User:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


def _identity(user: User, csrf_token: str) -> dict[str, Any]:
    return {"login": user.login, "role": user.role, "csrf_token": csrf_token}


@router.post("/login")
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    user = await authenticate(db, payload.login, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="invalid credentials")
    settings: Settings = request.app.state.settings
    session = await create_session(
        db, user, ttl=timedelta(hours=settings.session_ttl_hours)
    )
    set_session_cookie(
        response,
        session.token,
        ttl=timedelta(hours=settings.session_ttl_hours),
        secure=settings.cookie_secure,
    )
    return _identity(user, session.csrf_token)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        await revoke_session(db, token)
    clear_session_cookie(response)
    return {"status": "logged out"}


@router.get("/me")
async def me(
    request: Request, user: Annotated[User, Depends(current_user)]
) -> dict[str, Any]:
    return _identity(user, request.state.csrf_token)


@users_router.get("/users")
async def list_users_endpoint(
    _user: Annotated[User, Depends(current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[UserSummary]:
    return [
        UserSummary(login=user.login, role=user.role)
        for user in await list_users(db)
    ]
