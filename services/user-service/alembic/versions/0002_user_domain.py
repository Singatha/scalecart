"""Add users, roles, addresses, and rotating refresh tokens."""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "0002_user_domain"
down_revision = "0001_phase_1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CUSTOMER_ROLE_ID = "10000000-0000-0000-0000-000000000001"
ADMIN_ROLE_ID = "10000000-0000-0000-0000-000000000002"


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_roles_name"),
    )
    roles = sa.table(
        "roles",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("description", sa.String()),
    )
    op.bulk_insert(
        roles,
        [
            {
                "id": UUID(CUSTOMER_ROLE_ID),
                "name": "customer",
                "description": "Standard storefront customer",
            },
            {
                "id": UUID(ADMIN_ROLE_ID),
                "name": "admin",
                "description": "User administration access",
            },
        ],
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )
    op.create_table(
        "addresses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=50), nullable=False),
        sa.Column("recipient_name", sa.String(length=200), nullable=False),
        sa.Column("line1", sa.String(length=200), nullable=False),
        sa.Column("line2", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=100), nullable=False),
        sa.Column("postal_code", sa.String(length=32), nullable=False),
        sa.Column("country_code", sa.String(length=2), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "label", name="uq_addresses_user_label"),
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"])
    op.create_index(
        "uq_addresses_one_default_per_user",
        "addresses",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("jti", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"])
    op.create_index("ix_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=True)
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_jti", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_expires_at", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_index("uq_addresses_one_default_per_user", table_name="addresses")
    op.drop_index("ix_addresses_user_id", table_name="addresses")
    op.drop_table("addresses")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
