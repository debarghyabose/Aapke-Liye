"""claims.ai_state: Member 1's claim object, sent back on every claim-AI turn

Revision ID: 0002
Revises: 0001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("claims", sa.Column("ai_state", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("claims", "ai_state")
