"""add favorites table

Revision ID: c4b8a7f21d3e
Revises: bf3c9a09596e
Create Date: 2026-04-30 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4b8a7f21d3e'
down_revision = 'bf3c9a09596e'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'favorites',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('book_id', sa.Integer(), sa.ForeignKey('books.id'), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'book_id')
    )


def downgrade():
    op.drop_table('favorites')
