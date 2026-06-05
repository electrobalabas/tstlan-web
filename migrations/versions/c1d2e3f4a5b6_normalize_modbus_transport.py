"""normalize modbus transport and backfill variable indexes

Revision ID: c1d2e3f4a5b6
Revises: a1b2c3d4e5f6
Create Date: 2026-06-04 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Any, cast

import sqlalchemy as sa
from alembic import op


revision: str = 'c1d2e3f4a5b6'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Типизированная JSON-колонка: SQLAlchemy сам (де)сериализует payload под
# SQLite (TEXT) и PostgreSQL (json/jsonb), поэтому в коде он всегда dict.
device_configs = sa.table(
    "device_configs",
    sa.column("id", sa.Integer),
    sa.column("payload", sa.JSON),
)


def _migrate(
    transport_map: dict[str, str],
    *,
    backfill_index: bool = False,
    strip_index: bool = False,
) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(device_configs.c.id, device_configs.c.payload)
    ).all()
    for row_id, raw_payload in rows:
        if not isinstance(raw_payload, dict):
            continue
        payload = cast(dict[str, Any], raw_payload)
        changed = False

        connection = payload.get("connection")
        if isinstance(connection, dict):
            conn = cast(dict[str, Any], connection)
            if conn.get("transport") in transport_map:
                conn["transport"] = transport_map[conn["transport"]]
                changed = True

        variables = payload.get("variables")
        if isinstance(variables, list):
            for position, item in enumerate(variables):
                if not isinstance(item, dict):
                    continue
                variable = cast(dict[str, Any], item)
                if backfill_index and "index" not in variable:
                    variable["index"] = position
                    changed = True
                if strip_index and "index" in variable:
                    del variable["index"]
                    changed = True

        if changed:
            bind.execute(
                sa.update(device_configs)
                .where(device_configs.c.id == row_id)
                .values(payload=payload)
            )


def upgrade() -> None:
    _migrate({"modbus": "modbus_tcp"}, backfill_index=True)


def downgrade() -> None:
    _migrate(
        {"modbus_tcp": "modbus", "modbus_udp": "modbus"}, strip_index=True
    )
