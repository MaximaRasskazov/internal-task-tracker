"""Pydantic 2 transport contracts for the task tracker's domain API."""

from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Annotated, ClassVar, Literal, Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from email_validator import EmailNotValidError, validate_email
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    JsonValue,
    StrictBool,
    StringConstraints,
    model_validator,
)
from pydantic.config import JsonDict
from pydantic.json_schema import SkipJsonSchema

Role = Literal["admin", "pm", "developer"]
Priority = Literal["low", "medium", "high"]
ColumnCategory = Literal["todo", "in_progress", "done"]
AnalyticsPeriod = Literal["week", "month", "all"]


def _uppercase(value: object) -> object:
    return value.upper() if isinstance(value, str) else value


def _normalize_email(value: object) -> object:
    return value.strip().lower() if isinstance(value, str) else value


def _limit_email(value: str) -> str:
    if len(value) > 254:
        raise ValueError("Email must contain at most 254 characters")
    return value


def _validated_email(value: str) -> str:
    try:
        validated = validate_email(value, check_deliverability=False, test_environment=True)
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc
    return _limit_email(validated.normalized.lower())


def _iana_timezone(value: str) -> str:
    try:
        ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("Use a valid IANA timezone identifier") from exc
    return value


def _calendar_date(value: object) -> object:
    if type(value) is date:
        return value
    if isinstance(value, str):
        # fromisoformat also accepts basic and ISO-week dates; the API does not.
        if (
            len(value) == 10
            and value[4] == "-"
            and value[7] == "-"
            and all("0" <= char <= "9" for char in value[:4] + value[5:7] + value[8:])
        ):
            return date.fromisoformat(value)
    raise ValueError("Use a calendar date in YYYY-MM-DD format")


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _unique_ids(value: list[UUID]) -> list[UUID]:
    if len(value) != len(set(value)):
        raise ValueError("IDs must be unique")
    return value


def _omit_patch_default(schema: JsonDict) -> None:
    # None represents omission internally, but is not a valid wire value.
    schema.pop("default", None)


Name = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=100)
]
PersonName = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=80)
]
Title = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]
TagName = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=40)
]
CommentText = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=5000)
]
ProjectDescription = Annotated[str, StringConstraints(strict=True, max_length=2000)]
TaskDescription = Annotated[str, StringConstraints(strict=True, max_length=20000)]
ProjectKey = Annotated[
    str,
    StringConstraints(strict=True, pattern=r"^[A-Z][A-Z0-9]{1,7}$"),
    BeforeValidator(_uppercase),
]
Email = Annotated[
    str,
    StringConstraints(strict=True, max_length=254),
    BeforeValidator(_normalize_email),
    AfterValidator(_validated_email),
]
Timezone = Annotated[str, StringConstraints(strict=True), AfterValidator(_iana_timezone)]
Color = Annotated[str, StringConstraints(strict=True, pattern=r"^#[0-9A-Fa-f]{6}$")]
CalendarDate = Annotated[date, BeforeValidator(_calendar_date)]
Timestamp = Annotated[AwareDatetime, AfterValidator(_utc)]
NonNegativeInt = Annotated[int, Field(strict=True, ge=0)]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]
StoryPoints = Annotated[int, Field(strict=True, ge=0, le=100)]
TagIds = Annotated[list[UUID], Field(max_length=20), AfterValidator(_unique_ids)]
UniqueIds = Annotated[list[UUID], AfterValidator(_unique_ids)]


class ReadDto(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, serialize_by_alias=True)


class WriteDto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PatchWriteDto(WriteDto):
    """Distinguish omission from null and reject control-only PATCH requests."""

    nullable_fields: ClassVar[frozenset[str]] = frozenset()
    control_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="before")
    @classmethod
    def validate_patch(cls, data: object) -> object:
        if isinstance(data, Mapping):
            changed = set(data) & (cls.model_fields.keys() - cls.control_fields)
            if not changed:
                raise ValueError("Provide at least one field to change")
            for field in changed - cls.nullable_fields:
                if data[field] is None:
                    raise ValueError(f"{field} cannot be null")
        return data


class Person(ReadDto):
    id: UUID
    name: str


class UserDto(ReadDto):
    id: UUID
    name: str
    email: str
    role: Role
    is_active: StrictBool
    created_at: Timestamp


class SessionDto(ReadDto):
    user: UserDto
    csrf_token: str
    expires_at: Timestamp


class ProjectDto(ReadDto):
    id: UUID
    key: str
    name: str
    description: str
    owner_id: UUID
    timezone: str
    member_count: NonNegativeInt
    board_count: NonNegativeInt
    created_at: Timestamp
    updated_at: Timestamp


class MemberDto(ReadDto):
    user_id: UUID
    name: str
    email: str
    is_active: StrictBool
    is_owner: StrictBool
    joined_at: Timestamp


class BoardDto(ReadDto):
    id: UUID
    project_id: UUID
    name: str
    revision: NonNegativeInt
    created_at: Timestamp
    updated_at: Timestamp


class ColumnDto(ReadDto):
    id: UUID
    board_id: UUID
    name: str
    category: ColumnCategory
    position: NonNegativeInt


class TagDto(ReadDto):
    id: UUID
    project_id: UUID
    name: str
    color: str


class TaskDto(ReadDto):
    id: UUID
    project_id: UUID
    board_id: UUID
    number: PositiveInt
    key: str
    title: str
    description: str
    column_id: UUID
    position: NonNegativeInt
    priority: Priority
    author_id: UUID
    author: Person
    assignee_id: UUID | None
    assignee: Person | None
    assignee_is_project_member: StrictBool
    deadline: CalendarDate | None
    story_points: StoryPoints | None
    tag_ids: list[UUID]
    version: PositiveInt
    is_completed: StrictBool
    created_at: Timestamp
    updated_at: Timestamp


class CommentDto(ReadDto):
    id: UUID
    task_id: UUID
    author_id: UUID
    author: Person
    text: str
    created_at: Timestamp


class Change(ReadDto):
    field: str
    old_value: JsonValue
    new_value: JsonValue


class AuditDto(ReadDto):
    id: UUID
    task_id: UUID
    operation_id: UUID
    event_type: str
    changes: list[Change]
    actor_id: UUID
    actor: Person
    occurred_at: Timestamp


class BoardSnapshot(ReadDto):
    board: BoardDto
    project: ProjectDto
    revision: NonNegativeInt
    server_time: Timestamp
    columns: list[ColumnDto]
    tasks: list[TaskDto]
    members: list[MemberDto]
    tags: list[TagDto]

    @model_validator(mode="after")
    def consistent_revision(self) -> Self:
        if self.revision != self.board.revision:
            raise ValueError("Snapshot revision must match its board revision")
        return self


class TaskList(ReadDto):
    items: list[TaskDto]
    total: NonNegativeInt
    board_revision: NonNegativeInt


class MutationResponse[T](ReadDto):
    data: T
    board_id: UUID
    board_revision: NonNegativeInt


class TaskRead(MutationResponse[TaskDto]):
    pass


class PaginatedList[T](ReadDto):
    items: list[T]
    total: NonNegativeInt
    limit: Annotated[int, Field(strict=True, ge=1, le=100)]
    offset: NonNegativeInt


class StatusDistribution(ReadDto):
    board_id: UUID
    board_name: str
    column_id: UUID
    column_name: str
    category: ColumnCategory
    count: NonNegativeInt


class CompletionPoint(ReadDto):
    date: CalendarDate
    completed_count: NonNegativeInt


class AnalyticsDto(ReadDto):
    project_id: UUID
    timezone: str
    period: AnalyticsPeriod
    from_date: CalendarDate = Field(alias="from")
    to: CalendarDate
    granularity: Literal["day", "month"]
    generated_at: Timestamp
    status_distribution: list[StatusDistribution]
    completion_over_time: list[CompletionPoint]


class ProjectCreate(WriteDto):
    key: ProjectKey
    name: Name
    description: ProjectDescription = ""
    timezone: Timezone = "UTC"


class ProjectPatch(PatchWriteDto):
    name: Name | SkipJsonSchema[None] = Field(default=None, json_schema_extra=_omit_patch_default)
    description: ProjectDescription | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_patch_default
    )


class OwnerChange(WriteDto):
    user_id: UUID


class MemberCreate(WriteDto):
    email: Email


class BoardCreate(WriteDto):
    name: Name


class BoardPatch(WriteDto):
    name: Name


class ColumnCreate(WriteDto):
    name: Name
    category: ColumnCategory


class ColumnPatch(WriteDto):
    name: Name


class ColumnOrder(WriteDto):
    column_ids: UniqueIds
    expected_revision: NonNegativeInt


class TaskCreate(WriteDto):
    title: Title
    column_id: UUID
    description: TaskDescription = ""
    priority: Priority = "medium"
    assignee_id: UUID | None = None
    deadline: CalendarDate | None = None
    story_points: StoryPoints | None = None
    tag_ids: TagIds = Field(default_factory=list)


class TaskPatch(PatchWriteDto):
    nullable_fields = frozenset({"assignee_id", "deadline", "story_points"})
    control_fields = frozenset({"expected_version"})

    expected_version: PositiveInt
    title: Title | SkipJsonSchema[None] = Field(default=None, json_schema_extra=_omit_patch_default)
    description: TaskDescription | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_patch_default
    )
    priority: Priority | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_patch_default
    )
    assignee_id: UUID | None = None
    deadline: CalendarDate | None = None
    story_points: StoryPoints | None = None
    tag_ids: TagIds | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_patch_default
    )


class TaskMove(WriteDto):
    column_id: UUID
    before_task_id: UUID | None
    expected_version: PositiveInt


class TagCreate(WriteDto):
    name: TagName
    color: Color = "#64748B"


class TagPatch(PatchWriteDto):
    name: TagName | SkipJsonSchema[None] = Field(
        default=None, json_schema_extra=_omit_patch_default
    )
    color: Color | SkipJsonSchema[None] = Field(default=None, json_schema_extra=_omit_patch_default)


class CommentCreate(WriteDto):
    text: CommentText


class RoleChange(WriteDto):
    role: Role
