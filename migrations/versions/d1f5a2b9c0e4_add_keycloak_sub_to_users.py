"""add keycloak_sub to users and relax password_hash

Revision ID: d1f5a2b9c0e4
Revises: b9c4d8e1a2f3
Create Date: 2026-05-04 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd1f5a2b9c0e4'
down_revision = 'b9c4d8e1a2f3'
branch_labels = None
depends_on = None


def upgrade():
    # password_hash is no longer the source of truth — Keycloak owns
    # credentials. Kept nullable rather than dropped so existing rows
    # don't violate the constraint and the column can be removed in a
    # follow-up once nothing reads it.
    op.alter_column("users", "password_hash", existing_type=sa.String(length=200), nullable=True)
    op.add_column("users", sa.Column("keycloak_sub", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_users_keycloak_sub", "users", ["keycloak_sub"])
    op.create_index("ix_users_keycloak_sub", "users", ["keycloak_sub"])


def downgrade():
    op.drop_index("ix_users_keycloak_sub", table_name="users")
    op.drop_constraint("uq_users_keycloak_sub", "users", type_="unique")
    op.drop_column("users", "keycloak_sub")
    op.alter_column("users", "password_hash", existing_type=sa.String(length=200), nullable=False)
