"""add job queue_position

Revision ID: c4a8e1b2d3f0
Revises: 8aa33b55950e
Create Date: 2026-05-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c4a8e1b2d3f0"
down_revision: Union[str, Sequence[str], None] = "8aa33b55950e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("queue_position", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("jobs", "queue_position")
