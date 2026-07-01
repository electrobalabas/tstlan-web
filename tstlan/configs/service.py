import logging

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from tstlan.auth.models import Role, User
from tstlan.configs.models import (
    ConfigShare,
    ConfigVisibility,
    DeviceConfig,
    SharePermission,
)
from tstlan.configs.schemas import Access, ConfigCreate, ConfigUpdate, ShareRequest
from tstlan.logging_setup import get_service_logger, log_event

logger = get_service_logger("configs")


class ConfigNotFound(Exception):
    pass


class ConfigAccessDenied(Exception):
    pass


class PublishNotAllowed(Exception):
    pass


class GranteeNotFound(Exception):
    pass


class CannotShareWithOwner(Exception):
    pass


def effective_access(user: User, config: DeviceConfig) -> Access | None:
    """Доступ пользователя к конфигу."""
    if user.role is Role.ADMIN or config.owner_id == user.id:
        return Access.OWNER
    permission = _share_permission(user, config)
    if permission is SharePermission.WRITE:
        return Access.WRITE
    if permission is SharePermission.READ:
        return Access.READ
    if config.visibility is ConfigVisibility.PUBLIC:
        return Access.READ
    return None


def _share_permission(user: User, config: DeviceConfig) -> SharePermission | None:
    for share in config.shares:
        if share.grantee_id == user.id:
            return share.permission
    return None


def _can_publish(user: User) -> bool:
    return user.role in (Role.DEV, Role.ADMIN)


def _resolve_create_visibility(
    user: User, visibility: ConfigVisibility
) -> ConfigVisibility:
    # PUBLIC - явный флаг публикации (только dev/admin). Непубличный конфиг при
    # создании остаётся PRIVATE; метку SHARED выставляет шаринг.
    if visibility is ConfigVisibility.PUBLIC:
        if not _can_publish(user):
            log_event(
                logger,
                logging.WARNING,
                "configs.publish.rejected",
                login=user.login,
                user_id=user.id,
                role=user.role,
            )
            raise PublishNotAllowed(user.login)
        return ConfigVisibility.PUBLIC
    return ConfigVisibility.PRIVATE


def _normalize_visibility(config: DeviceConfig) -> None:
    # PRIVATE/SHARED - производная метка от наличия грантов; PUBLIC не трогаем.
    if config.visibility is ConfigVisibility.PUBLIC:
        return
    config.visibility = (
        ConfigVisibility.SHARED if config.shares else ConfigVisibility.PRIVATE
    )


async def _load_detail(db: AsyncSession, config_id: int) -> DeviceConfig:
    # После мутации перечитываем конфиг с жадной загрузкой owner/shares/grantee,
    # чтобы сериализация ответа не дёргала ленивые relationship (MissingGreenlet).
    result = await db.execute(
        select(DeviceConfig)
        .where(DeviceConfig.id == config_id)
        .options(
            selectinload(DeviceConfig.owner),
            selectinload(DeviceConfig.shares).selectinload(ConfigShare.grantee),
        )
        .execution_options(populate_existing=True)
    )
    return result.scalar_one()


async def list_configs(
    db: AsyncSession, user: User
) -> list[tuple[DeviceConfig, Access]]:
    stmt = select(DeviceConfig)
    if user.role is not Role.ADMIN:
        stmt = (
            stmt.outerjoin(
                ConfigShare,
                and_(
                    ConfigShare.config_id == DeviceConfig.id,
                    ConfigShare.grantee_id == user.id,
                ),
            )
            .where(
                or_(
                    DeviceConfig.owner_id == user.id,
                    DeviceConfig.visibility == ConfigVisibility.PUBLIC,
                    ConfigShare.id.is_not(None),
                )
            )
            .distinct()
        )
    stmt = stmt.order_by(DeviceConfig.updated_at.desc())
    configs = (await db.execute(stmt)).scalars().unique().all()
    result: list[tuple[DeviceConfig, Access]] = []
    for config in configs:
        access = effective_access(user, config)
        if access is not None:
            result.append((config, access))
    log_event(
        logger,
        logging.DEBUG,
        "configs.listed",
        login=user.login,
        user_id=user.id,
        role=user.role,
        count=len(result),
    )
    return result


async def get_config(
    db: AsyncSession, user: User, config_id: int
) -> tuple[DeviceConfig, Access]:
    config = await db.get(DeviceConfig, config_id)
    if config is None:
        log_event(logger, logging.WARNING, "configs.not_found", config_id=config_id)
        raise ConfigNotFound(config_id)
    access = effective_access(user, config)
    if access is None:
        log_event(
            logger,
            logging.WARNING,
            "configs.access.denied",
            config_id=config_id,
            login=user.login,
            user_id=user.id,
        )
        raise ConfigAccessDenied(config_id)
    return config, access


async def create_config(
    db: AsyncSession, user: User, data: ConfigCreate
) -> DeviceConfig:
    config = DeviceConfig(
        owner_id=user.id,
        name=data.name,
        device_type=data.device_type,
        payload=data.payload.model_dump(mode="json"),
        visibility=_resolve_create_visibility(user, data.visibility),
    )
    db.add(config)
    await db.commit()
    config = await _load_detail(db, config.id)
    log_event(
        logger,
        logging.INFO,
        "configs.created",
        config_id=config.id,
        login=user.login,
        user_id=user.id,
        visibility=config.visibility,
    )
    return config


async def update_config(
    db: AsyncSession, user: User, config_id: int, data: ConfigUpdate
) -> tuple[DeviceConfig, Access]:
    config, access = await get_config(db, user, config_id)
    wants_manage = data.name is not None or data.visibility is not None
    if wants_manage and access is not Access.OWNER:
        log_event(
            logger,
            logging.WARNING,
            "configs.update.rejected",
            config_id=config_id,
            login=user.login,
            user_id=user.id,
            reason="manage_requires_owner",
        )
        raise ConfigAccessDenied(config_id)
    if data.payload is not None and access not in (Access.OWNER, Access.WRITE):
        log_event(
            logger,
            logging.WARNING,
            "configs.update.rejected",
            config_id=config_id,
            login=user.login,
            user_id=user.id,
            reason="payload_requires_write",
        )
        raise ConfigAccessDenied(config_id)

    if data.visibility is not None:
        if data.visibility is ConfigVisibility.PUBLIC:
            if not _can_publish(user):
                log_event(
                    logger,
                    logging.WARNING,
                    "configs.publish.rejected",
                    config_id=config_id,
                    login=user.login,
                    user_id=user.id,
                    role=user.role,
                )
                raise PublishNotAllowed(user.login)
            config.visibility = ConfigVisibility.PUBLIC
        else:
            config.visibility = ConfigVisibility.PRIVATE
            _normalize_visibility(config)
    if data.name is not None:
        config.name = data.name
    if data.payload is not None:
        config.payload = data.payload.model_dump(mode="json")

    await db.commit()
    config = await _load_detail(db, config_id)
    log_event(
        logger,
        logging.INFO,
        "configs.updated",
        config_id=config_id,
        login=user.login,
        user_id=user.id,
        access=access,
    )
    return config, effective_access(user, config) or access


async def delete_config(db: AsyncSession, user: User, config_id: int) -> None:
    config, access = await get_config(db, user, config_id)
    if access is not Access.OWNER:
        log_event(
            logger,
            logging.WARNING,
            "configs.delete.rejected",
            config_id=config_id,
            login=user.login,
            user_id=user.id,
        )
        raise ConfigAccessDenied(config_id)
    await db.delete(config)
    await db.commit()
    log_event(
        logger,
        logging.INFO,
        "configs.deleted",
        config_id=config_id,
        login=user.login,
        user_id=user.id,
    )


async def share_config(
    db: AsyncSession, user: User, config_id: int, req: ShareRequest
) -> tuple[DeviceConfig, Access]:
    config, access = await get_config(db, user, config_id)
    if access is not Access.OWNER:
        log_event(
            logger,
            logging.WARNING,
            "configs.share.rejected",
            config_id=config_id,
            login=user.login,
            user_id=user.id,
            reason="owner_required",
        )
        raise ConfigAccessDenied(config_id)
    grantee = (
        await db.execute(select(User).where(User.login == req.login))
    ).scalar_one_or_none()
    if grantee is None:
        log_event(
            logger,
            logging.WARNING,
            "configs.share.rejected",
            config_id=config_id,
            login=user.login,
            grantee=req.login,
            reason="grantee_not_found",
        )
        raise GranteeNotFound(req.login)
    if grantee.id == config.owner_id:
        log_event(
            logger,
            logging.WARNING,
            "configs.share.rejected",
            config_id=config_id,
            login=user.login,
            grantee=req.login,
            reason="grantee_is_owner",
        )
        raise CannotShareWithOwner(req.login)

    existing = next((s for s in config.shares if s.grantee_id == grantee.id), None)
    if existing is not None:
        existing.permission = req.permission
    else:
        config.shares.append(
            ConfigShare(grantee_id=grantee.id, permission=req.permission)
        )
    _normalize_visibility(config)
    await db.commit()
    log_event(
        logger,
        logging.INFO,
        "configs.shared",
        config_id=config_id,
        login=user.login,
        user_id=user.id,
        grantee=req.login,
        permission=req.permission,
    )
    return await _load_detail(db, config_id), access


async def unshare_config(
    db: AsyncSession, user: User, config_id: int, login: str
) -> tuple[DeviceConfig, Access]:
    config, access = await get_config(db, user, config_id)
    if access is not Access.OWNER:
        log_event(
            logger,
            logging.WARNING,
            "configs.unshare.rejected",
            config_id=config_id,
            login=user.login,
            user_id=user.id,
        )
        raise ConfigAccessDenied(config_id)
    share = next((s for s in config.shares if s.grantee.login == login), None)
    if share is None:
        log_event(
            logger,
            logging.WARNING,
            "configs.unshare.rejected",
            config_id=config_id,
            login=user.login,
            grantee=login,
            reason="grantee_not_found",
        )
        raise GranteeNotFound(login)
    config.shares.remove(share)
    _normalize_visibility(config)
    await db.commit()
    log_event(
        logger,
        logging.INFO,
        "configs.unshared",
        config_id=config_id,
        login=user.login,
        user_id=user.id,
        grantee=login,
    )
    return await _load_detail(db, config_id), access
