"""Add orders and immutable order items."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0002_orders"
down_revision = "0001_phase_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.String(length=32), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=True),
        sa.Column("checkout_identity", sa.String(length=80), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("guest_token_hash", sa.String(length=64), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("subtotal_amount", sa.BigInteger(), nullable=False),
        sa.Column("shipping_amount", sa.BigInteger(), nullable=False),
        sa.Column("total_amount", sa.BigInteger(), nullable=False),
        sa.Column("delivery_method", sa.String(length=20), nullable=False),
        sa.Column("recipient_name", sa.String(length=200), nullable=False),
        sa.Column("address_line1", sa.String(length=200), nullable=False),
        sa.Column("address_line2", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('reserving_inventory', 'pending_payment', 'confirmed', 'processing', "
            "'shipped', 'delivered', 'cancelled', 'checkout_failed')",
            name="ck_orders_status",
        ),
        sa.CheckConstraint("subtotal_amount >= 0", name="ck_orders_subtotal_nonnegative"),
        sa.CheckConstraint("shipping_amount >= 0", name="ck_orders_shipping_nonnegative"),
        sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
        sa.UniqueConstraint("number", name="uq_orders_number"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_orders_customer_created", "orders", ["customer_id", "created_at"])
    op.create_index("ix_orders_number", "orders", ["number"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_table(
        "order_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("variant_id", sa.Uuid(), nullable=False),
        sa.Column("product_slug", sa.String(length=220), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("variant_name", sa.String(length=120), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_amount", sa.BigInteger(), nullable=False),
        sa.Column("line_total_amount", sa.BigInteger(), nullable=False),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price_amount >= 0", name="ck_order_items_price_nonnegative"),
        sa.CheckConstraint("line_total_amount >= 0", name="ck_order_items_total_nonnegative"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_number", table_name="orders")
    op.drop_index("ix_orders_customer_created", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
