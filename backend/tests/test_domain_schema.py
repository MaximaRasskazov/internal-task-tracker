"""Transport validation and serialization checks for the domain API."""

import json
from datetime import UTC, date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.schemas.domain import (
    AnalyticsDto,
    BoardCreate,
    BoardDto,
    BoardPatch,
    BoardSnapshot,
    Change,
    ColumnCreate,
    ColumnOrder,
    ColumnPatch,
    CommentCreate,
    MemberCreate,
    MutationResponse,
    OwnerChange,
    PaginatedList,
    ProjectCreate,
    ProjectDto,
    ProjectPatch,
    RoleChange,
    TagCreate,
    TagPatch,
    TaskCreate,
    TaskMove,
    TaskPatch,
    UserDto,
)

ID = UUID("d9970814-8f0f-4b3a-a2a9-c65856efc9d2")
NOW = datetime(2026, 9, 11, 10, tzinfo=UTC)


def test_create_defaults_and_selective_normalization() -> None:
    project = ProjectCreate(key="task", name="  Разработка  ", description="  text\n")
    assert (project.key, project.name, project.description, project.timezone) == (
        "TASK",
        "Разработка",
        "  text\n",
        "UTC",
    )
    task = TaskCreate(title="  Новая задача  ", column_id=ID)
    assert task.model_dump() == {
        "title": "Новая задача",
        "column_id": ID,
        "description": "",
        "priority": "medium",
        "assignee_id": None,
        "deadline": None,
        "story_points": None,
        "tag_ids": [],
    }
    assert MemberCreate(email="  MEMBER@Example.COM ").email == "member@example.com"
    assert CommentCreate(text="  line one\nline two  ").text == "line one\nline two"
    assert TagCreate(name="Work").color == "#64748B"


def test_demo_email_accepts_reserved_test_domain() -> None:
    assert MemberCreate(email="  ADMIN@EXAMPLE.TEST ").email == "admin@example.test"


@pytest.mark.parametrize(
    "email",
    ["bad@@example.test", "bad @example.test", "@example.test", "bad@", "bad@example..test"],
)
def test_demo_email_still_rejects_invalid_syntax(email: str) -> None:
    with pytest.raises(ValidationError):
        MemberCreate(email=email)


@pytest.mark.parametrize("key", ["A", "ABCDEFGHI", "1AB", "AB-CD", "АБ", " AB", "AB\n"])
def test_project_key_rejects_invalid_format(key: str) -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(key=key, name="Project")


@pytest.mark.parametrize("zone", ["Not/A_Timezone", "../UTC", "", " UTC "])
def test_project_timezone_rejects_unknown_or_non_iana_values(zone: str) -> None:
    with pytest.raises(ValidationError):
        ProjectCreate(key="AB", name="Project", timezone=zone)


def test_valid_project_timezone() -> None:
    assert ProjectCreate(key="AB", name="Project", timezone="Asia/Yekaterinburg").timezone == (
        "Asia/Yekaterinburg"
    )


@pytest.mark.parametrize("value", [True, False, 1.0, 1.5, "3", -1, 101])
def test_story_points_must_be_an_integer_in_range(value: object) -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"title": "Task", "column_id": ID, "story_points": value})


@pytest.mark.parametrize("value", [None, 0, 100])
def test_valid_story_points(value: int | None) -> None:
    assert TaskCreate(title="Task", column_id=ID, story_points=value).story_points == value


@pytest.mark.parametrize("value", [True, False, 1.0, "1", 0, -1, None])
def test_version_must_be_a_positive_integer(value: object) -> None:
    with pytest.raises(ValidationError):
        TaskPatch.model_validate({"expected_version": value, "title": "Task"})


@pytest.mark.parametrize("value", [True, 0.0, "0", -1])
def test_revision_must_be_a_nonnegative_integer(value: object) -> None:
    with pytest.raises(ValidationError):
        ColumnOrder.model_validate({"expected_revision": value, "column_ids": []})


@pytest.mark.parametrize(
    "value",
    [
        "2026-02-30",
        "2026-9-11",
        "20260911",
        "2026-W37-5",
        "2026-09-11T00:00:00Z",
        "2026-09-11T00:00:00+05:00",
        "2026-09-11 ",
        1789084800,
        True,
        NOW,
    ],
)
def test_deadline_rejects_timestamps_and_invalid_calendar_dates(value: object) -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"title": "Task", "column_id": ID, "deadline": value})


def test_deadline_preserves_the_calendar_date() -> None:
    task = TaskCreate.model_validate({"title": "Task", "column_id": ID, "deadline": "2028-02-29"})
    assert task.deadline == date(2028, 2, 29)
    assert task.model_dump(mode="json")["deadline"] == "2028-02-29"


@pytest.mark.parametrize("model", [ProjectPatch, TagPatch, BoardPatch, ColumnPatch])
def test_empty_patch_is_rejected(
    model: type[ProjectPatch | TagPatch | BoardPatch | ColumnPatch],
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({})


def test_task_patch_requires_a_change_in_addition_to_version() -> None:
    with pytest.raises(ValidationError):
        TaskPatch(expected_version=1)
    with pytest.raises(ValidationError):
        TaskPatch.model_validate({"title": "Task"})


@pytest.mark.parametrize("field", ["title", "description", "priority", "tag_ids"])
def test_task_patch_rejects_null_for_nonnullable_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        TaskPatch.model_validate({"expected_version": 1, field: None})


@pytest.mark.parametrize("field", ["assignee_id", "deadline", "story_points"])
def test_task_patch_preserves_explicit_null_and_omits_missing_fields(field: str) -> None:
    patch = TaskPatch.model_validate({"expected_version": 1, field: None})
    assert patch.model_fields_set == {"expected_version", field}
    assert patch.model_dump(exclude_unset=True) == {"expected_version": 1, field: None}


@pytest.mark.parametrize(
    "model,field",
    [
        (ProjectPatch, "name"),
        (ProjectPatch, "description"),
        (TagPatch, "name"),
        (TagPatch, "color"),
    ],
)
def test_container_patch_rejects_explicit_null(
    model: type[ProjectPatch | TagPatch], field: str
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate({field: None})


def test_patch_omitted_values_do_not_replace_existing_fields() -> None:
    assert ProjectPatch(name="Renamed").model_dump(exclude_unset=True) == {"name": "Renamed"}
    assert TaskPatch(expected_version=3, tag_ids=[]).model_dump(exclude_unset=True) == {
        "expected_version": 3,
        "tag_ids": [],
    }


@pytest.mark.parametrize(
    "model,nonnullable,payload",
    [
        (ProjectPatch, {"name", "description"}, {"name": "Renamed"}),
        (
            TaskPatch,
            {"title", "description", "priority", "tag_ids"},
            {"expected_version": 1, "assignee_id": None},
        ),
        (TagPatch, {"name", "color"}, {"name": "Renamed"}),
    ],
)
def test_patch_openapi_distinguishes_omission_from_nullable_values(
    model: type[ProjectPatch | TaskPatch | TagPatch],
    nonnullable: set[str],
    payload: dict[str, object],
) -> None:
    schema = model.model_json_schema()
    required = schema.get("required", [])
    for field in nonnullable:
        property_schema = schema["properties"][field]
        assert field not in required
        assert property_schema.get("type") in {"string", "array"}
        assert "anyOf" not in property_schema
        assert "default" not in property_schema
        with pytest.raises(ValidationError):
            model.model_validate({**payload, field: None})
    assert model.model_validate(payload).model_dump(exclude_unset=True) == payload


@pytest.mark.parametrize("field", ["assignee_id", "deadline", "story_points"])
def test_task_patch_openapi_preserves_explicitly_nullable_fields(field: str) -> None:
    schema = TaskPatch.model_json_schema()
    assert {"type": "null"} in schema["properties"][field]["anyOf"]
    assert field not in schema["required"]
    patch = TaskPatch.model_validate({"expected_version": 1, field: None})
    assert patch.model_dump(exclude_unset=True) == {"expected_version": 1, field: None}


@pytest.mark.parametrize("field", ["column_id", "position", "author_id", "version", "unknown"])
def test_task_patch_rejects_server_owned_and_move_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        TaskPatch.model_validate({"expected_version": 1, "title": "Task", field: 1})


@pytest.mark.parametrize(
    "model,payload",
    [
        (ProjectCreate, {"key": "AB", "name": "Project"}),
        (ProjectPatch, {"name": "Project"}),
        (OwnerChange, {"user_id": ID}),
        (MemberCreate, {"email": "member@example.com"}),
        (BoardCreate, {"name": "Board"}),
        (BoardPatch, {"name": "Board"}),
        (ColumnCreate, {"name": "Column", "category": "todo"}),
        (ColumnPatch, {"name": "Column"}),
        (ColumnOrder, {"column_ids": [], "expected_revision": 0}),
        (TaskCreate, {"title": "Task", "column_id": ID}),
        (TaskMove, {"column_id": ID, "before_task_id": None, "expected_version": 1}),
        (TagCreate, {"name": "Tag"}),
        (TagPatch, {"name": "Tag"}),
        (CommentCreate, {"text": "Comment"}),
        (RoleChange, {"role": "developer"}),
    ],
)
def test_all_write_contracts_reject_unknown_fields(
    model: type[ProjectCreate], payload: dict[str, object]
) -> None:
    with pytest.raises(ValidationError) as error:
        model.model_validate({**payload, "server_owned": "injected"})
    assert any(issue["type"] == "extra_forbidden" for issue in error.value.errors())


def test_tag_set_limits_and_duplicates_after_uuid_parsing() -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"title": "Task", "column_id": ID, "tag_ids": [ID, str(ID)]})
    with pytest.raises(ValidationError):
        TaskCreate(title="Task", column_id=ID, tag_ids=[uuid4() for _ in range(21)])
    assert (
        len(TaskCreate(title="Task", column_id=ID, tag_ids=[uuid4() for _ in range(20)]).tag_ids)
        == 20
    )
    with pytest.raises(ValidationError):
        ColumnOrder(column_ids=[ID, ID], expected_revision=0)


@pytest.mark.parametrize("color", ["red", "#abc", "#11223344", "112233", "#GGHHII"])
def test_tag_color_requires_six_hex_digits(color: str) -> None:
    with pytest.raises(ValidationError):
        TagCreate(name="Tag", color=color)


def test_response_uses_utc_z_and_never_serializes_internal_attributes() -> None:
    row = SimpleNamespace(
        id=ID,
        name="Member",
        email="member@example.com",
        role="developer",
        is_active=True,
        created_at=datetime(2026, 9, 11, 15, tzinfo=timezone(timedelta(hours=5))),
        password_hash="private",
        csrf_hash="private",
        next_task_number=123,
    )
    user = UserDto.model_validate(row)
    data = json.loads(user.model_dump_json())
    assert data == {
        "id": str(ID),
        "name": "Member",
        "email": "member@example.com",
        "role": "developer",
        "is_active": True,
        "created_at": "2026-09-11T10:00:00Z",
    }
    row.created_at = datetime(2026, 9, 11, 10)
    with pytest.raises(ValidationError):
        UserDto.model_validate(row)


def test_analytics_uses_exact_external_field_names() -> None:
    analytics = AnalyticsDto.model_validate(
        {
            "project_id": ID,
            "timezone": "UTC",
            "period": "week",
            "from": "2026-09-05",
            "to": "2026-09-11",
            "granularity": "day",
            "generated_at": NOW,
            "status_distribution": [],
            "completion_over_time": [{"date": "2026-09-05", "completed_count": 0}],
        }
    )
    output = analytics.model_dump(mode="json")
    assert output["from"] == "2026-09-05"
    assert "from_date" not in output
    assert output["generated_at"] == "2026-09-11T10:00:00Z"
    assert output["completion_over_time"] == [{"date": "2026-09-05", "completed_count": 0}]


def test_snapshot_rejects_mismatched_revision() -> None:
    project = ProjectDto(
        id=ID,
        key="AB",
        name="Project",
        description="",
        owner_id=ID,
        timezone="UTC",
        member_count=1,
        board_count=1,
        created_at=NOW,
        updated_at=NOW,
    )
    board = BoardDto(id=ID, project_id=ID, name="Board", revision=2, created_at=NOW, updated_at=NOW)
    with pytest.raises(ValidationError):
        BoardSnapshot(
            board=board,
            project=project,
            revision=1,
            server_time=NOW,
            columns=[],
            tasks=[],
            members=[],
            tags=[],
        )


def test_generic_responses_and_audit_json_values() -> None:
    deleted = MutationResponse[None](data=None, board_id=ID, board_revision=3)
    assert deleted.model_dump(mode="json") == {
        "data": None,
        "board_id": str(ID),
        "board_revision": 3,
    }
    page = PaginatedList[Change](
        items=[Change(field="tags", old_value=None, new_value={"names": ["New"], "count": 1})],
        total=1,
        limit=50,
        offset=0,
    )
    assert page.items[0].new_value == {"names": ["New"], "count": 1}
    with pytest.raises(ValidationError):
        Change.model_validate({"field": "bad", "old_value": None, "new_value": object()})


@pytest.mark.parametrize(
    "model,payload",
    [
        (ProjectCreate, {"key": "AB", "name": " "}),
        (ProjectCreate, {"key": "AB", "name": "A" * 101}),
        (ProjectCreate, {"key": "AB", "name": "Project", "description": "A" * 2001}),
        (TaskCreate, {"title": " ", "column_id": ID}),
        (TaskCreate, {"title": "A" * 201, "column_id": ID}),
        (TaskCreate, {"title": "Task", "column_id": ID, "description": "A" * 20001}),
        (TagCreate, {"name": "A" * 41}),
        (CommentCreate, {"text": " "}),
        (CommentCreate, {"text": "A" * 5001}),
        (MemberCreate, {"email": "not an email"}),
    ],
)
def test_text_constraints(model: type[ProjectCreate], payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(payload)
