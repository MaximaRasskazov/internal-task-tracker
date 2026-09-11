"""Relational domain; services own transactions, ordering, and explicit updated_at changes."""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models import Role  # noqa: F401 -- register the referenced role table


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) BETWEEN 1 AND 80", name="name_length"),
        CheckConstraint("email = lower(btrim(email))", name="email_normalized"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"), default="developer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (CheckConstraint("expires_at > created_at", name="expiry_after_creation"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint("key ~ '^[A-Z][A-Z0-9]{1,7}$'", name="key_format"),
        CheckConstraint("length(btrim(name)) BETWEEN 1 AND 100", name="name_length"),
        CheckConstraint("length(description) <= 2000", name="description_length"),
        CheckConstraint("next_task_number >= 1", name="positive_task_number"),
        ForeignKeyConstraint(
            ["id", "owner_id"],
            ["project_members.project_id", "project_members.user_id"],
            name="fk_projects_owner_membership",
            use_alter=True,
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    key: Mapped[str] = mapped_column(String(8), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    timezone: Mapped[str] = mapped_column(String(100), default="UTC", server_default="UTC")
    next_task_number: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class ProjectMember(Base):
    __tablename__ = "project_members"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Board(Base):
    __tablename__ = "boards"
    __table_args__ = (
        UniqueConstraint("id", "project_id", name="uq_boards_id_project_id"),
        CheckConstraint("revision >= 0", name="nonnegative_revision"),
        CheckConstraint("length(btrim(name)) BETWEEN 1 AND 100", name="name_length"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    revision: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Column(Base):
    __tablename__ = "columns"
    __table_args__ = (
        UniqueConstraint("id", "board_id", name="uq_columns_id_board_id"),
        CheckConstraint("category IN ('todo', 'in_progress', 'done')", name="valid_category"),
        CheckConstraint("position >= 0", name="nonnegative_position"),
        CheckConstraint("length(btrim(name)) BETWEEN 1 AND 100", name="name_length"),
        Index("ix_columns_board_position", "board_id", "position"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    board_id: Mapped[UUID] = mapped_column(ForeignKey("boards.id"))
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(16))
    position: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint("project_id", "number", name="uq_tasks_project_number"),
        UniqueConstraint("id", "project_id", "board_id", name="uq_tasks_id_project_board"),
        ForeignKeyConstraint(
            ["board_id", "project_id"],
            ["boards.id", "boards.project_id"],
            name="fk_tasks_board_project",
        ),
        ForeignKeyConstraint(
            ["column_id", "board_id"],
            ["columns.id", "columns.board_id"],
            name="fk_tasks_column_board",
        ),
        CheckConstraint("number >= 1", name="positive_number"),
        CheckConstraint("version >= 1", name="positive_version"),
        CheckConstraint("position >= 0", name="nonnegative_position"),
        CheckConstraint("priority IN ('low', 'medium', 'high')", name="valid_priority"),
        CheckConstraint(
            "story_points IS NULL OR story_points BETWEEN 0 AND 100", name="story_points_range"
        ),
        CheckConstraint("length(btrim(title)) BETWEEN 1 AND 200", name="title_length"),
        CheckConstraint("length(description) <= 20000", name="description_length"),
        Index(
            "ix_tasks_active_board_order",
            "board_id",
            "column_id",
            "position",
            "id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_tasks_project_assignee_deadline", "project_id", "assignee_id", "deadline"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    board_id: Mapped[UUID] = mapped_column()
    number: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="", server_default="")
    column_id: Mapped[UUID] = mapped_column()
    position: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String(6), default="medium", server_default="medium")
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    assignee_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    deadline: Mapped[date | None] = mapped_column(Date)
    story_points: Mapped[int | None] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(BigInteger, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("project_id", "normalized_name", name="uq_tags_project_normalized_name"),
        CheckConstraint("length(btrim(name)) BETWEEN 1 AND 40", name="name_length"),
        CheckConstraint("color ~ '^#[0-9A-Fa-f]{6}$'", name="color_format"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(40))
    normalized_name: Mapped[str] = mapped_column(
        String(40), Computed("lower(btrim(name))", persisted=True)
    )
    color: Mapped[str] = mapped_column(String(7), default="#64748B", server_default="#64748B")


class TaskTag(Base):
    __tablename__ = "task_tags"

    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"), primary_key=True)
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("tags.id"), primary_key=True, index=True)


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint("length(btrim(text)) BETWEEN 1 AND 5000", name="text_length"),
        Index("ix_comments_task_created", "task_id", "created_at", "id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(ForeignKey("tasks.id"))
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["task_id", "project_id", "board_id"],
            ["tasks.id", "tasks.project_id", "tasks.board_id"],
            name="fk_audit_events_task_project_board",
        ),
        CheckConstraint(
            "event_type IN ('task.created', 'task.updated', 'task.moved', 'task.completed', "
            "'task.reopened', 'task.deleted', 'comment.created')",
            name="valid_event_type",
        ),
        CheckConstraint("jsonb_typeof(changes) = 'array'", name="changes_array"),
        Index("ix_audit_events_task_occurred", "task_id", "occurred_at", "id"),
        Index("ix_audit_events_project_type_occurred", "project_id", "event_type", "occurred_at"),
        Index("ix_audit_events_board_occurred", "board_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column()
    project_id: Mapped[UUID] = mapped_column()
    board_id: Mapped[UUID] = mapped_column()
    operation_id: Mapped[UUID] = mapped_column(default=uuid4)
    event_type: Mapped[str] = mapped_column(String(32))
    changes: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
