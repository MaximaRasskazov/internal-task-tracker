from datetime import UTC, date, datetime
from uuid import uuid4

from app.db.domain import Project
from app.services.analytics import calendar_buckets, calendar_range


def project(timezone: str = "UTC", created: datetime | None = None) -> Project:
    return Project(
        id=uuid4(),
        key="TEAM",
        name="Team",
        owner_id=uuid4(),
        timezone=timezone,
        created_at=created or datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_week_uses_local_calendar_and_dst_boundary() -> None:
    # March 8 is a 23-hour day in New York. March 9 03:30 UTC is still March 8 locally.
    first, last, granularity, start, end = calendar_range(
        project("America/New_York"), "week", datetime(2026, 3, 9, 3, 30, tzinfo=UTC)
    )
    assert (first, last, granularity) == (date(2026, 3, 2), date(2026, 3, 8), "day")
    assert start == datetime(2026, 3, 2, 5, tzinfo=UTC)
    assert end == datetime(2026, 3, 9, 4, tzinfo=UTC)
    assert (end - start).total_seconds() == 167 * 3600


def test_month_is_thirty_inclusive_calendar_days() -> None:
    first, last, granularity, _, _ = calendar_range(
        project(), "month", datetime(2026, 9, 11, 8, tzinfo=UTC)
    )
    assert len(calendar_buckets(first, last, granularity)) == 30
    assert (first, last) == (date(2026, 8, 13), date(2026, 9, 11))


def test_all_switches_to_month_only_above_ninety_days() -> None:
    reference = project(created=datetime(2026, 1, 1, tzinfo=UTC))
    assert calendar_range(reference, "all", datetime(2026, 3, 31, tzinfo=UTC))[2] == "day"
    first, last, granularity, _, _ = calendar_range(
        reference, "all", datetime(2026, 4, 1, tzinfo=UTC)
    )
    assert granularity == "month"
    assert calendar_buckets(first, last, granularity) == [
        date(2026, 1, 1),
        date(2026, 2, 1),
        date(2026, 3, 1),
        date(2026, 4, 1),
    ]


def test_partial_months_and_year_rollover_include_zero_buckets() -> None:
    assert calendar_buckets(date(2025, 12, 15), date(2026, 2, 8), "month") == [
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]


def test_all_starts_on_project_local_creation_date() -> None:
    reference = project("Asia/Yekaterinburg", datetime(2026, 9, 9, 21, tzinfo=UTC))
    first, last, _, start, _ = calendar_range(
        reference, "all", datetime(2026, 9, 11, 14, tzinfo=UTC)
    )
    assert (first, last) == (date(2026, 9, 10), date(2026, 9, 11))
    assert start == datetime(2026, 9, 9, 19, tzinfo=UTC)
