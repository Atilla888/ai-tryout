"""add user_number running number to users

Gives every user a short, human-readable sequential number alongside the
existing public_id UUID. Existing users are backfilled in signup order so their
numbers are stable; new users get MAX(user_number)+1 from the application layer.

Revision ID: 9f1c7a2b4d3e
Revises: 28bdd812010b
Create Date: 2026-07-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '9f1c7a2b4d3e'
down_revision: Union[str, Sequence[str], None] = '28bdd812010b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add the column as nullable so existing rows can be backfilled first.
    op.add_column('users', sa.Column('user_number', sa.Integer(), nullable=True))

    # 2. Backfill existing users with a running number in signup order
    #    (oldest first), so #1 is the first user who ever registered.
    op.execute(
        """
        WITH ordered AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS rn
            FROM users
        )
        UPDATE users
        SET user_number = ordered.rn
        FROM ordered
        WHERE users.id = ordered.id
        """
    )

    # 3. Now that every row has a value, enforce NOT NULL + uniqueness.
    op.alter_column('users', 'user_number', existing_type=sa.Integer(), nullable=False)
    op.create_unique_constraint(op.f('uq_users_user_number'), 'users', ['user_number'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f('uq_users_user_number'), 'users', type_='unique')
    op.drop_column('users', 'user_number')
