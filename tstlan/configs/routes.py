from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.models import User
from tstlan.auth.routes import current_user, get_db
from tstlan.configs.schemas import (
    ConfigCreate,
    ConfigDetail,
    ConfigSummary,
    ConfigUpdate,
    ShareRequest,
)
from tstlan.configs.service import (
    CannotShareWithOwner,
    ConfigAccessDenied,
    ConfigNotFound,
    GranteeNotFound,
    PublishNotAllowed,
    create_config,
    delete_config,
    get_config,
    list_configs,
    share_config,
    unshare_config,
    update_config,
)
from tstlan.logging_setup import get_logger

router = APIRouter(prefix="/configs", tags=["configs"])
logger = get_logger(__name__)

Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


@router.get("")
async def list_endpoint(user: CurrentUser, db: Db) -> list[ConfigSummary]:
    return [
        ConfigSummary.from_config(config, access)
        for config, access in await list_configs(db, user)
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_endpoint(
    payload: ConfigCreate, user: CurrentUser, db: Db
) -> ConfigDetail:
    config = await create_config(db, user, payload)
    _, access = await get_config(db, user, config.id)
    logger.info(
        "config created",
        extra={"config_id": config.id, "login": user.login},
    )
    return ConfigDetail.from_config(config, access)


@router.get("/{config_id}")
async def get_endpoint(config_id: int, user: CurrentUser, db: Db) -> ConfigDetail:
    config, access = await get_config(db, user, config_id)
    return ConfigDetail.from_config(config, access)


@router.put("/{config_id}")
async def update_endpoint(
    config_id: int, payload: ConfigUpdate, user: CurrentUser, db: Db
) -> ConfigDetail:
    config, access = await update_config(db, user, config_id, payload)
    logger.info("config updated", extra={"config_id": config_id, "login": user.login})
    return ConfigDetail.from_config(config, access)


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_endpoint(config_id: int, user: CurrentUser, db: Db) -> Response:
    await delete_config(db, user, config_id)
    logger.info("config deleted", extra={"config_id": config_id, "login": user.login})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{config_id}/shares")
async def share_endpoint(
    config_id: int, payload: ShareRequest, user: CurrentUser, db: Db
) -> ConfigDetail:
    config, access = await share_config(db, user, config_id, payload)
    logger.info(
        "config shared",
        extra={
            "config_id": config_id,
            "login": user.login,
            "grantee": payload.login,
            "permission": payload.permission,
        },
    )
    return ConfigDetail.from_config(config, access)


@router.delete("/{config_id}/shares/{login}")
async def unshare_endpoint(
    config_id: int, login: str, user: CurrentUser, db: Db
) -> ConfigDetail:
    config, access = await unshare_config(db, user, config_id, login)
    logger.info(
        "config unshared",
        extra={"config_id": config_id, "login": user.login, "grantee": login},
    )
    return ConfigDetail.from_config(config, access)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ConfigNotFound, _not_found)
    app.add_exception_handler(GranteeNotFound, _not_found)
    app.add_exception_handler(ConfigAccessDenied, _forbidden)
    app.add_exception_handler(PublishNotAllowed, _forbidden)
    app.add_exception_handler(CannotShareWithOwner, _unprocessable)


def _not_found(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=404)


def _forbidden(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=403)


def _unprocessable(_request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse({"detail": str(exc)}, status_code=422)
