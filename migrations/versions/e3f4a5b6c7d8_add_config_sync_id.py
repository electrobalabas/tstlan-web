from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op


revision: str = 'e3f4a5b6c7d8'
down_revision: str | None = 'd2e3f4a5b6c7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


device_configs = sa.table(
    "device_configs",
    sa.column("id", sa.Integer),
    sa.column("sync_id", sa.String(length=36)),
)


def upgrade() -> None:
    with op.batch_alter_table("device_configs", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sync_id", sa.String(length=36), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.select(device_configs.c.id)).all()
    for (config_id,) in rows:
        bind.execute(
            sa.update(device_configs)
            .where(device_configs.c.id == config_id)
            .values(sync_id=str(uuid4()))
        )

    with op.batch_alter_table("device_configs", schema=None) as batch_op:
        batch_op.alter_column("sync_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_index(
            batch_op.f("ix_device_configs_sync_id"), ["sync_id"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("device_configs", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_device_configs_sync_id"))
        batch_op.drop_column("sync_id")
