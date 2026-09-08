"""Add order status history and reservation expiry."""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0003_order_lifecycle"
down_revision = "0002_orders"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORDER_STATUSES = (
    "'reserving_inventory', 'pending_payment', 'confirmed', 'processing', "
    "'shipped', 'delivered', 'cancelled', 'checkout_failed'"
)


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("reservation_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_orders_reservation_expiry",
        "orders",
        ["status", "reservation_expires_at"],
    )
    op.execute(
        sa.text(
            "UPDATE orders SET reservation_expires_at = updated_at + interval '30 minutes' "
            "WHERE status IN ('reserving_inventory', 'pending_payment')"
        )
    )
    history = op.create_table(
        "order_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=True),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("actor_type", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            f"from_status IS NULL OR from_status IN ({ORDER_STATUSES})",
            name="ck_order_status_history_from_status",
        ),
        sa.CheckConstraint(
            f"to_status IN ({ORDER_STATUSES})",
            name="ck_order_status_history_to_status",
        ),
        sa.CheckConstraint(
            "actor_type IN ('system', 'customer', 'guest', 'admin', 'migration')",
            name="ck_order_status_history_actor_type",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_status_history_order_id", "order_status_history", ["order_id"])
    op.create_index(
        "ix_order_status_history_order_created",
        "order_status_history",
        ["order_id", "created_at"],
    )

    connection = op.get_bind()
    existing_orders = connection.execute(
        sa.text("SELECT id, status, updated_at FROM orders")
    ).mappings()
    rows = [
        {
            "id": uuid4(),
            "order_id": order["id"],
            "from_status": None,
            "to_status": order["status"],
            "actor_type": "migration",
            "actor_id": None,
            "reason": "phase_6_history_backfill",
            "created_at": order["updated_at"],
        }
        for order in existing_orders
    ]
    if rows:
        op.bulk_insert(history, rows)


def downgrade() -> None:
    op.drop_index("ix_order_status_history_order_created", table_name="order_status_history")
    op.drop_index("ix_order_status_history_order_id", table_name="order_status_history")
    op.drop_table("order_status_history")
    op.drop_index("ix_orders_reservation_expiry", table_name="orders")
    op.drop_column("orders", "reservation_expires_at")
