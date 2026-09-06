"""Add categories, products, variants, inventory, and images."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "0002_catalog"
down_revision = "0001_phase_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
    op.create_index("ix_categories_slug", "categories", ["slug"])

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("brand", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("featured", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("status IN ('draft', 'active', 'archived')", name="ck_products_status"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_products_slug"),
    )
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_category_status", "products", ["category_id", "status"])
    op.create_index("ix_products_slug", "products", ["slug"])

    op.create_table(
        "product_variants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("price_amount", sa.Integer(), nullable=False),
        sa.Column("compare_at_amount", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="ZAR", nullable=False),
        sa.Column("stock_quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("price_amount >= 0", name="ck_variants_price_nonnegative"),
        sa.CheckConstraint(
            "compare_at_amount IS NULL OR compare_at_amount >= price_amount",
            name="ck_variants_compare_at_price",
        ),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_variants_stock_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku", name="uq_product_variants_sku"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])
    op.create_index("ix_product_variants_sku", "product_variants", ["sku"])

    op.create_table(
        "product_images",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("url", sa.String(length=2048), nullable=False),
        sa.Column("alt_text", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("position >= 0", name="ck_product_images_position_nonnegative"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "position", name="uq_product_images_position"),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_table("product_images")
    op.drop_index("ix_product_variants_sku", table_name="product_variants")
    op.drop_index("ix_product_variants_product_id", table_name="product_variants")
    op.drop_table("product_variants")
    op.drop_index("ix_products_slug", table_name="products")
    op.drop_index("ix_products_category_status", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_table("categories")
