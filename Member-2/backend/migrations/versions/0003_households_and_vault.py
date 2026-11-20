"""households, vault_documents tables and claims.household_id

Revision ID: 0003
Revises: 0002
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "vault_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("household_id", sa.String(length=20), nullable=False),
        sa.Column("doc_type", sa.String(length=60), nullable=False),
        sa.Column("filename_label", sa.String(length=120), nullable=False),
        sa.Column("path", sa.String(length=300), nullable=False),
        sa.Column("content_type", sa.String(length=60), nullable=False),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["household_id"], ["households.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("vault_documents", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_vault_documents_household_id"), ["household_id"], unique=False
        )
    # Add household_id FK to claims (batch mode for SQLite)
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("household_id", sa.String(length=20), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_claims_household_id", "households", ["household_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("claims", schema=None) as batch_op:
        batch_op.drop_constraint("fk_claims_household_id", type_="foreignkey")
        batch_op.drop_column("household_id")
    with op.batch_alter_table("vault_documents", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_vault_documents_household_id"))
    op.drop_table("vault_documents")
    op.drop_table("households")
