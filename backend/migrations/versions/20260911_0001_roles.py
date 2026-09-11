"""Create the global role lookup required by the product specification.

This is the T01 migration proof. Full domain tables and demo data belong to T02.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260911_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    roles = op.create_table(
        "roles",
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.CheckConstraint("code IN ('admin', 'pm', 'developer')", name="ck_roles_valid_code"),
        sa.PrimaryKeyConstraint("code", name="pk_roles"),
    )
    op.bulk_insert(
        roles,
        [
            {"code": "admin", "name": "Администратор"},
            {"code": "pm", "name": "Менеджер проектов"},
            {"code": "developer", "name": "Разработчик"},
        ],
    )


def downgrade() -> None:
    op.drop_table("roles")
