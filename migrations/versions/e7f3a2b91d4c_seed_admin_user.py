"""seed admin user

Revision ID: e7f3a2b91d4c
Revises: 77e39e6d6197
Create Date: 2026-05-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash


# revision identifiers, used by Alembic.
revision = 'e7f3a2b91d4c'
down_revision = '77e39e6d6197'
branch_labels = None
depends_on = None


ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@tkc-library.local"
ADMIN_PASSWORD = "admin"


def upgrade():
    users_table = sa.table(
        "users",
        sa.column("username", sa.String),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("role", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    op.bulk_insert(
        users_table,
        [
            {
                "username": ADMIN_USERNAME,
                "email": ADMIN_EMAIL,
                "password_hash": generate_password_hash(ADMIN_PASSWORD),
                "role": "admin",
                "created_at": datetime.now(timezone.utc),
            },
        ],
    )


def downgrade():
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM users WHERE username = :username"),
        {"username": ADMIN_USERNAME},
    )
