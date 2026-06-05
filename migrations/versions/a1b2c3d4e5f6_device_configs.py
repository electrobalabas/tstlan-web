from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a1b2c3d4e5f6'
down_revision: str | None = '5e1414fa1ab4'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'device_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('device_type', sa.String(length=64), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column(
            'visibility',
            sa.Enum(
                'private', 'shared', 'public',
                name='configvisibility', native_enum=False, length=16,
            ),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('device_configs', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_device_configs_owner_id'), ['owner_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_device_configs_device_type'), ['device_type'], unique=False
        )

    op.create_table(
        'config_shares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('grantee_id', sa.Integer(), nullable=False),
        sa.Column(
            'permission',
            sa.Enum(
                'read', 'write',
                name='sharepermission', native_enum=False, length=16,
            ),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['config_id'], ['device_configs.id'], ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(['grantee_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'config_id', 'grantee_id', name='uq_config_share_grantee'
        ),
    )
    with op.batch_alter_table('config_shares', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_config_shares_config_id'), ['config_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_config_shares_grantee_id'), ['grantee_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('config_shares', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_config_shares_grantee_id'))
        batch_op.drop_index(batch_op.f('ix_config_shares_config_id'))
    op.drop_table('config_shares')

    with op.batch_alter_table('device_configs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_device_configs_device_type'))
        batch_op.drop_index(batch_op.f('ix_device_configs_owner_id'))
    op.drop_table('device_configs')
