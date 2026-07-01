import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tstlan.auth.models import Role, User
from tstlan.auth.service import create_user
from tstlan.configs.models import ConfigVisibility, SharePermission
from tstlan.configs.schemas import (
    Access,
    ConfigCreate,
    ConfigPayload,
    ConfigUpdate,
    ConfigVar,
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
    effective_access,
    get_config,
    list_configs,
    share_config,
    unshare_config,
    update_config,
)
from tstlan.models import NetVarCType

pytestmark = pytest.mark.anyio


async def _user(session: AsyncSession, login: str, role: Role = Role.USER) -> User:
    return await create_user(session, login=login, password="pw", role=role)


async def _make(
    session: AsyncSession,
    owner: User,
    *,
    name: str = "cfg",
    device_type: str = "multimeter",
    visibility: ConfigVisibility = ConfigVisibility.PRIVATE,
    payload: ConfigPayload | None = None,
):
    data = ConfigCreate(
        name=name,
        device_type=device_type,
        visibility=visibility,
        payload=payload or ConfigPayload(),
    )
    return await create_config(session, owner, data)


async def test_owner_has_full_access(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    config = await _make(session, owner)
    assert effective_access(owner, config) is Access.OWNER


async def test_stranger_has_no_access_to_private(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    stranger = await _user(session, "bob")
    config = await _make(session, owner)
    assert effective_access(stranger, config) is None


async def test_admin_has_full_access_to_any_config(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    admin = await _user(session, "root", Role.ADMIN)
    config = await _make(session, owner)
    assert effective_access(admin, config) is Access.OWNER


async def test_public_config_is_readable_by_strangers(session: AsyncSession) -> None:
    dev = await _user(session, "dev", Role.DEV)
    stranger = await _user(session, "bob")
    config = await _make(session, dev, visibility=ConfigVisibility.PUBLIC)
    assert effective_access(stranger, config) is Access.READ


async def test_user_cannot_publish(session: AsyncSession) -> None:
    user = await _user(session, "alice")
    with pytest.raises(PublishNotAllowed):
        await _make(session, user, visibility=ConfigVisibility.PUBLIC)


async def test_dev_can_publish(session: AsyncSession) -> None:
    dev = await _user(session, "dev", Role.DEV)
    config = await _make(session, dev, visibility=ConfigVisibility.PUBLIC)
    assert config.visibility is ConfigVisibility.PUBLIC


async def test_user_create_non_public_stays_private(session: AsyncSession) -> None:
    user = await _user(session, "alice")
    config = await _make(session, user, visibility=ConfigVisibility.SHARED)
    assert config.visibility is ConfigVisibility.PRIVATE


async def test_share_grants_read(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    await share_config(
        session,
        owner,
        config.id,
        ShareRequest(login="bob", permission=SharePermission.READ),
    )
    fetched, access = await get_config(session, bob, config.id)
    assert access is Access.READ
    assert fetched.visibility is ConfigVisibility.SHARED


async def test_share_grants_write(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    await share_config(
        session,
        owner,
        config.id,
        ShareRequest(login="bob", permission=SharePermission.WRITE),
    )
    assert effective_access(bob, config) is Access.WRITE


async def test_share_with_owner_is_rejected(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    config = await _make(session, owner)
    with pytest.raises(CannotShareWithOwner):
        await share_config(session, owner, config.id, ShareRequest(login="owner"))


async def test_share_unknown_grantee_is_rejected(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    config = await _make(session, owner)
    with pytest.raises(GranteeNotFound):
        await share_config(session, owner, config.id, ShareRequest(login="ghost"))


async def test_non_owner_cannot_share(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    with pytest.raises(ConfigAccessDenied):
        await share_config(session, bob, config.id, ShareRequest(login="bob"))


async def test_unshare_revokes_access_and_resets_visibility(
    session: AsyncSession,
) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    await share_config(session, owner, config.id, ShareRequest(login="bob"))
    updated, _ = await unshare_config(session, owner, config.id, "bob")
    assert effective_access(bob, updated) is None
    assert updated.visibility is ConfigVisibility.PRIVATE


async def test_write_grantee_can_edit_payload(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    await share_config(
        session,
        owner,
        config.id,
        ShareRequest(login="bob", permission=SharePermission.WRITE),
    )
    payload = ConfigPayload(
        variables=[ConfigVar(name="voltage", ctype=NetVarCType.F32, graph=True)]
    )
    updated, _ = await update_config(
        session, bob, config.id, ConfigUpdate(payload=payload)
    )
    assert updated.payload["variables"][0]["name"] == "voltage"


async def test_read_grantee_cannot_edit_payload(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    await share_config(session, owner, config.id, ShareRequest(login="bob"))
    with pytest.raises(ConfigAccessDenied):
        await update_config(
            session, bob, config.id, ConfigUpdate(payload=ConfigPayload())
        )


async def test_write_grantee_cannot_rename(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    await share_config(
        session,
        owner,
        config.id,
        ShareRequest(login="bob", permission=SharePermission.WRITE),
    )
    with pytest.raises(ConfigAccessDenied):
        await update_config(session, bob, config.id, ConfigUpdate(name="hacked"))


async def test_non_owner_cannot_delete(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    bob = await _user(session, "bob")
    config = await _make(session, owner)
    await share_config(
        session,
        owner,
        config.id,
        ShareRequest(login="bob", permission=SharePermission.WRITE),
    )
    with pytest.raises(ConfigAccessDenied):
        await delete_config(session, bob, config.id)


async def test_owner_can_delete(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    config = await _make(session, owner)
    await delete_config(session, owner, config.id)
    with pytest.raises(ConfigNotFound):
        await get_config(session, owner, config.id)


async def test_list_returns_owned_shared_and_public_only(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    dev = await _user(session, "dev", Role.DEV)
    bob = await _user(session, "bob")

    await _make(session, bob, name="own")
    shared = await _make(session, owner, name="shared")
    await share_config(session, owner, shared.id, ShareRequest(login="bob"))
    await _make(session, dev, name="public", visibility=ConfigVisibility.PUBLIC)
    await _make(session, owner, name="hidden")  # приватный, в выдачу не попадает

    names = {config.name for config, _ in await list_configs(session, bob)}
    assert names == {"own", "shared", "public"}


async def test_admin_lists_everything(session: AsyncSession) -> None:
    owner = await _user(session, "owner")
    admin = await _user(session, "root", Role.ADMIN)
    await _make(session, owner, name="a")
    await _make(session, owner, name="b")
    names = {config.name for config, _ in await list_configs(session, admin)}
    assert names == {"a", "b"}


async def test_get_missing_config_raises(session: AsyncSession) -> None:
    user = await _user(session, "alice")
    with pytest.raises(ConfigNotFound):
        await get_config(session, user, 999)
