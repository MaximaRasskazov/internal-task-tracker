"""Limit the provisioned runtime role to append-only audit and read-only migration state.

Revision ID: 20260911_0003
Revises: 20260911_0002
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260911_0003"
down_revision: str | Sequence[str] | None = "20260911_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # The native setup and Compose provision tracker separately from tracker_owner.
    # A role-agnostic test/migration environment remains usable without that role.
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tracker') THEN
            REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
              ON TABLE alembic_version FROM tracker;
            REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
              ON TABLE audit_events FROM tracker;
            GRANT SELECT ON TABLE alembic_version TO tracker;
            GRANT SELECT, INSERT ON TABLE audit_events TO tracker;
          END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # Rolling back application schema must not silently expand runtime privileges.
    pass
