"""drop variable index

Переменные хранятся упорядоченным списком, а смещение в памяти выводится из
порядка и типа (см. NetVarCType.byte_size), поэтому отдельное поле `index`
у переменных payload больше не нужно.

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-06-05 00:00:00.000000

"""

from collections.abc import Callable, Sequence
from typing import Any, cast

import sqlalchemy as sa
from alembic import op


revision: str = 'd2e3f4a5b6c7'
down_revision: str | None = 'c1d2e3f4a5b6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

device_configs = sa.table(
    "device_configs",
    sa.column("id", sa.Integer),
    sa.column("payload", sa.JSON),
)


def _rewrite_variables(mutate: Callable[[dict[str, Any], int], bool]) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(device_configs.c.id, device_configs.c.payload)
    ).all()
    for row_id, raw_payload in rows:
        if not isinstance(raw_payload, dict):
            continue
        payload = cast(dict[str, Any], raw_payload)
        variables = payload.get("variables")
        if not isinstance(variables, list):
            continue
        changed = False
        for position, item in enumerate(variables):
            if isinstance(item, dict):
                changed |= mutate(cast(dict[str, Any], item), position)
        if changed:
            bind.execute(
                sa.update(device_configs)
                .where(device_configs.c.id == row_id)
                .values(payload=payload)
            )


def _strip_index(variable: dict[str, Any], position: int) -> bool:
    if "index" in variable:
        del variable["index"]
        return True
    return False


def _backfill_index(variable: dict[str, Any], position: int) -> bool:
    if "index" not in variable:
        variable["index"] = position
        return True
    return False


def upgrade() -> None:
    _rewrite_variables(_strip_index)


def downgrade() -> None:
    # Исходные разрежённые адреса не восстановить — раскладываем по позиции.
    _rewrite_variables(_backfill_index)
