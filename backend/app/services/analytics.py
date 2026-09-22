"""Project analytics from two SQL aggregates, with project-local calendar boundaries."""

from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Date, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.domain import AuditEvent, Board, Column, Project, Task

type Period = Literal["week", "month", "all"]
type Granularity = Literal["day", "month"]


class StatusDistribution(BaseModel):
    board_id: UUID
    board_name: str
    column_id: UUID
    column_name: str
    category: Literal["todo", "in_progress", "done"]
    count: int


class CompletionBucket(BaseModel):
    date: date
    completed_count: int


class AnalyticsDto(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    project_id: UUID
    timezone: str
    period: Period
    date_from: date = Field(alias="from")
    to: date
    granularity: Granularity
    generated_at: datetime
    status_distribution: list[StatusDistribution]
    completion_over_time: list[CompletionBucket]


def calendar_range(
    project: Project, period: Period, now: datetime
) -> tuple[date, date, Granularity, datetime, datetime]:
    """UTC bounds are half-open and include the entire last local calendar day."""
    zone = ZoneInfo(project.timezone)
    today = now.astimezone(zone).date()
    if period == "all":
        first = min(project.created_at.astimezone(zone).date(), today)
    else:
        first = today - timedelta(days=6 if period == "week" else 29)
    granularity: Granularity = "month" if (today - first).days >= 90 else "day"
    start = datetime.combine(first, time.min, tzinfo=zone).astimezone(UTC)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=zone).astimezone(UTC)
    return first, today, granularity, start, end


def calendar_buckets(first: date, last: date, granularity: Granularity) -> list[date]:
    current = first if granularity == "day" else first.replace(day=1)
    dates = []
    while current <= last:
        dates.append(current)
        if granularity == "day":
            current += timedelta(days=1)
        else:
            current = date(current.year + current.month // 12, current.month % 12 + 1, 1)
    return dates


async def project_analytics(
    session: AsyncSession,
    project: Project,
    period: Period = "month",
    *,
    now: datetime | None = None,
) -> AnalyticsDto:
    generated = now or datetime.now(UTC)
    first, last, granularity, start, end = calendar_range(project, period, generated)
    statuses = await session.execute(
        select(
            Board.id.label("board_id"),
            Board.name.label("board_name"),
            Column.id.label("column_id"),
            Column.name.label("column_name"),
            Column.category,
            func.count(Task.id).label("count"),
        )
        .join(Column, Column.board_id == Board.id)
        .outerjoin(Task, and_(Task.column_id == Column.id, Task.deleted_at.is_(None)))
        .where(Board.project_id == project.id)
        .group_by(Board.id, Board.name, Board.created_at, Column.id)
        .order_by(Board.created_at, Board.id, Column.position, Column.id)
    )
    # Period filtering must follow MIN over the entire history, including deleted tasks.
    # Otherwise a re-completion inside the period would become a false first completion.
    first_completions = (
        select(AuditEvent.task_id, func.min(AuditEvent.occurred_at).label("completed_at"))
        .where(AuditEvent.project_id == project.id, AuditEvent.event_type == "task.completed")
        .group_by(AuditEvent.task_id)
        .subquery()
    )
    local_timestamp = func.timezone(project.timezone, first_completions.c.completed_at)
    bucket = cast(
        func.date_trunc("month", local_timestamp) if granularity == "month" else local_timestamp,
        Date,
    )
    counts = await session.execute(
        select(bucket.label("date"), func.count().label("count"))
        .where(first_completions.c.completed_at >= start, first_completions.c.completed_at < end)
        .group_by(bucket)
        .order_by(bucket)
    )
    per_date = {row["date"]: row["count"] for row in counts.mappings()}
    return AnalyticsDto(
        project_id=project.id,
        timezone=project.timezone,
        period=period,
        date_from=first,
        to=last,
        granularity=granularity,
        generated_at=generated,
        status_distribution=[StatusDistribution(**dict(row)) for row in statuses.mappings()],
        completion_over_time=[
            CompletionBucket(date=day, completed_count=per_date.get(day, 0))
            for day in calendar_buckets(first, last, granularity)
        ],
    )
