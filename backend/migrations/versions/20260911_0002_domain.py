"""Create the task-tracker domain and protect append-only audit events."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260911_0002"
down_revision: str | Sequence[str] | None = "20260911_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role_code", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("email = lower(btrim(email))", name=op.f("ck_users_email_normalized")),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 80", name=op.f("ck_users_name_length")
        ),
        sa.ForeignKeyConstraint(
            ["role_code"], ["roles.code"], name=op.f("fk_users_role_code_roles")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("csrf_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "expires_at > created_at", name=op.f("ck_auth_sessions_expiry_after_creation")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_sessions_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
    )
    op.create_index(
        op.f("ix_auth_sessions_expires_at"), "auth_sessions", ["expires_at"], unique=False
    )
    op.create_index(op.f("ix_auth_sessions_user_id"), "auth_sessions", ["user_id"], unique=False)
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=8), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("timezone", sa.String(length=100), server_default="UTC", nullable=False),
        sa.Column("next_task_number", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("key ~ '^[A-Z][A-Z0-9]{1,7}$'", name=op.f("ck_projects_key_format")),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 100", name=op.f("ck_projects_name_length")
        ),
        sa.CheckConstraint(
            "length(description) <= 2000", name=op.f("ck_projects_description_length")
        ),
        sa.CheckConstraint("next_task_number >= 1", name=op.f("ck_projects_positive_task_number")),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_projects_owner_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint("key", name=op.f("uq_projects_key")),
    )
    op.create_table(
        "boards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("revision", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 100", name=op.f("ck_boards_name_length")
        ),
        sa.CheckConstraint("revision >= 0", name=op.f("ck_boards_nonnegative_revision")),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_boards_project_id_projects")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_boards")),
        sa.UniqueConstraint("id", "project_id", name="uq_boards_id_project_id"),
    )
    op.create_index(op.f("ix_boards_project_id"), "boards", ["project_id"], unique=False)
    op.create_table(
        "project_members",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_members_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_project_members_user_id_users")
        ),
        sa.PrimaryKeyConstraint("project_id", "user_id", name=op.f("pk_project_members")),
    )
    op.create_index(
        op.f("ix_project_members_user_id"), "project_members", ["user_id"], unique=False
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=40), nullable=False),
        sa.Column(
            "normalized_name",
            sa.String(length=40),
            sa.Computed("lower(btrim(name))", persisted=True),
            nullable=False,
        ),
        sa.Column("color", sa.String(length=7), server_default="#64748B", nullable=False),
        sa.CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name=op.f("ck_tags_color_format")),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 40", name=op.f("ck_tags_name_length")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_tags_project_id_projects")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tags")),
        sa.UniqueConstraint(
            "project_id", "normalized_name", name="uq_tags_project_normalized_name"
        ),
    )
    op.create_table(
        "columns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=16), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('todo', 'in_progress', 'done')", name=op.f("ck_columns_valid_category")
        ),
        sa.CheckConstraint(
            "length(btrim(name)) BETWEEN 1 AND 100", name=op.f("ck_columns_name_length")
        ),
        sa.CheckConstraint("position >= 0", name=op.f("ck_columns_nonnegative_position")),
        sa.ForeignKeyConstraint(
            ["board_id"], ["boards.id"], name=op.f("fk_columns_board_id_boards")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_columns")),
        sa.UniqueConstraint("id", "board_id", name="uq_columns_id_board_id"),
    )
    op.create_index("ix_columns_board_position", "columns", ["board_id", "position"], unique=False)
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), server_default="", nullable=False),
        sa.Column("column_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(length=6), server_default="medium", nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("assignee_id", sa.Uuid(), nullable=True),
        sa.Column("deadline", sa.Date(), nullable=True),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high')", name=op.f("ck_tasks_valid_priority")
        ),
        sa.CheckConstraint(
            "length(btrim(title)) BETWEEN 1 AND 200", name=op.f("ck_tasks_title_length")
        ),
        sa.CheckConstraint(
            "length(description) <= 20000", name=op.f("ck_tasks_description_length")
        ),
        sa.CheckConstraint("number >= 1", name=op.f("ck_tasks_positive_number")),
        sa.CheckConstraint("position >= 0", name=op.f("ck_tasks_nonnegative_position")),
        sa.CheckConstraint(
            "story_points IS NULL OR story_points BETWEEN 0 AND 100",
            name=op.f("ck_tasks_story_points_range"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_tasks_positive_version")),
        sa.ForeignKeyConstraint(
            ["assignee_id"], ["users.id"], name=op.f("fk_tasks_assignee_id_users")
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], name=op.f("fk_tasks_author_id_users")),
        sa.ForeignKeyConstraint(
            ["board_id", "project_id"],
            ["boards.id", "boards.project_id"],
            name="fk_tasks_board_project",
        ),
        sa.ForeignKeyConstraint(
            ["column_id", "board_id"],
            ["columns.id", "columns.board_id"],
            name="fk_tasks_column_board",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_tasks_project_id_projects")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tasks")),
        sa.UniqueConstraint("id", "project_id", "board_id", name="uq_tasks_id_project_board"),
        sa.UniqueConstraint("project_id", "number", name="uq_tasks_project_number"),
    )
    op.create_index(
        "ix_tasks_active_board_order",
        "tasks",
        ["board_id", "column_id", "position", "id"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_tasks_project_assignee_deadline",
        "tasks",
        ["project_id", "assignee_id", "deadline"],
        unique=False,
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("board_id", sa.Uuid(), nullable=False),
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('task.created', 'task.updated', 'task.moved', 'task.completed', "
            "'task.reopened', 'task.deleted', 'comment.created')",
            name=op.f("ck_audit_events_valid_event_type"),
        ),
        sa.CheckConstraint(
            "jsonb_typeof(changes) = 'array'", name=op.f("ck_audit_events_changes_array")
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name=op.f("fk_audit_events_actor_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["task_id", "project_id", "board_id"],
            ["tasks.id", "tasks.project_id", "tasks.board_id"],
            name="fk_audit_events_task_project_board",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_events")),
    )
    op.create_index(
        "ix_audit_events_board_occurred", "audit_events", ["board_id", "occurred_at"], unique=False
    )
    op.create_index(
        "ix_audit_events_project_type_occurred",
        "audit_events",
        ["project_id", "event_type", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_events_task_occurred",
        "audit_events",
        ["task_id", "occurred_at", "id"],
        unique=False,
    )
    op.create_table(
        "comments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(text)) BETWEEN 1 AND 5000", name=op.f("ck_comments_text_length")
        ),
        sa.ForeignKeyConstraint(
            ["author_id"], ["users.id"], name=op.f("fk_comments_author_id_users")
        ),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_comments_task_id_tasks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_comments")),
    )
    op.create_index(
        "ix_comments_task_created", "comments", ["task_id", "created_at", "id"], unique=False
    )
    op.create_table(
        "task_tags",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("tag_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], name=op.f("fk_task_tags_tag_id_tags")),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], name=op.f("fk_task_tags_task_id_tasks")),
        sa.PrimaryKeyConstraint("task_id", "tag_id", name=op.f("pk_task_tags")),
    )
    op.create_index(op.f("ix_task_tags_tag_id"), "task_tags", ["tag_id"], unique=False)

    # The owner must join the project in the same transaction that creates it.
    op.create_foreign_key(
        "fk_projects_owner_membership",
        "projects",
        "project_members",
        ["id", "owner_id"],
        ["project_id", "user_id"],
        deferrable=True,
        initially="DEFERRED",
    )
    op.execute(
        """
        CREATE FUNCTION reject_audit_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only'
                USING ERRCODE = '42501';
        END;
        $$
        """
    )
    # A statement trigger also rejects empty updates and truncation by table owners.
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE OR TRUNCATE ON audit_events
        FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_event_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER audit_events_append_only ON audit_events")
    op.execute("DROP FUNCTION reject_audit_event_mutation()")
    op.drop_constraint("fk_projects_owner_membership", "projects", type_="foreignkey")
    op.drop_table("task_tags")
    op.drop_table("comments")
    op.drop_table("audit_events")
    op.drop_table("tasks")
    op.drop_table("columns")
    op.drop_table("tags")
    op.drop_table("project_members")
    op.drop_table("boards")
    op.drop_table("projects")
    op.drop_table("auth_sessions")
    op.drop_table("users")
