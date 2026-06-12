"""add book_requests table

Revision ID: a1b2c3d4e5f6
Revises: d1f5a2b9c0e4
Create Date: 2026-06-12 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'd1f5a2b9c0e4'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'book_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('author', sa.String(length=120), nullable=False),
        sa.Column('link', sa.String(length=500), nullable=False),
        sa.Column('requested_by_user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by_user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('book_requests')
