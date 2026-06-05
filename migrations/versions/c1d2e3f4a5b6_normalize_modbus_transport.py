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


def _remap_transport(transport_map: dict[str, str]) -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.select(device_configs.c.id, device_configs.c.payload)
    ).all()
    for row_id, raw_payload in rows:
        if not isinstance(raw_payload, dict):
            continue
        payload = cast(dict[str, Any], raw_payload)
        connection = payload.get("connection")
        if not isinstance(connection, dict):
            continue
        conn = cast(dict[str, Any], connection)
        if conn.get("transport") in transport_map:
            conn["transport"] = transport_map[conn["transport"]]
            bind.execute(
                sa.update(device_configs)
                .where(device_configs.c.id == row_id)
                .values(payload=payload)
            )


def upgrade() -> None:
    _remap_transport({"modbus": "modbus_tcp"})


def downgrade() -> None:
    _remap_transport({"modbus_tcp": "modbus", "modbus_udp": "modbus"})
