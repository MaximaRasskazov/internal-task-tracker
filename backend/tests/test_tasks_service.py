"""Task behavior against migrated PostgreSQL and the real HTTP/auth stack."""

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.domain import Board, Column, Project, ProjectMember, Tag, Task, User
from tests.support import login

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class TaskBoard:
    project: Project
    board: Board
    todo: Column
    doing: Column
    done: Column
    tag_a: Tag
    tag_b: Tag
    foreign_column: Column
    foreign_tag: Tag


@pytest.fixture
async def task_board(db: AsyncSession, users: dict[str, User]) -> TaskBoard:
    project = Project(key="TASK", name="Task tests", owner_id=users["pm"].id)
    foreign_project = Project(key="OTHER", name="Private", owner_id=users["second_pm"].id)
    db.add_all([project, foreign_project])
    await db.flush()
    db.add_all(
        ProjectMember(project_id=project.id, user_id=users[name].id)
        for name in ("pm", "developer", "developer_b")
    )
    db.add(ProjectMember(project_id=foreign_project.id, user_id=users["second_pm"].id))
    board = Board(project_id=project.id, name="Engineering")
    foreign_board = Board(project_id=foreign_project.id, name="Private board")
    db.add_all([board, foreign_board])
    await db.flush()
    todo = Column(board_id=board.id, name="Todo", category="todo", position=0)
    doing = Column(board_id=board.id, name="Doing", category="in_progress", position=1)
    done = Column(board_id=board.id, name="Done", category="done", position=2)
    foreign_column = Column(
        board_id=foreign_board.id, name="Private todo", category="todo", position=0
    )
    tag_a = Tag(project_id=project.id, name="API")
    tag_b = Tag(project_id=project.id, name="Release")
    foreign_tag = Tag(project_id=foreign_project.id, name="Private tag")
    db.add_all([todo, doing, done, foreign_column, tag_a, tag_b, foreign_tag])
    await db.commit()
    return TaskBoard(project, board, todo, doing, done, tag_a, tag_b, foreign_column, foreign_tag)


async def create_task(
    client: AsyncClient,
    board: TaskBoard,
    title: str = "Implement task behavior",
    **fields: Any,
) -> dict[str, Any]:
    response = await client.post(
        f"/api/v1/boards/{board.board.id}/tasks",
        json={"title": title, "column_id": str(board.todo.id), **fields},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def task_history(client: AsyncClient, task_id: str) -> list[dict[str, Any]]:
    response = await client.get(f"/api/v1/tasks/{task_id}/history")
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def read_task(client: AsyncClient, task_id: str) -> dict[str, Any]:
    response = await client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def test_create_update_noop_and_stale_version_preserve_atomic_audit(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard
) -> None:
    await login(client, users["developer"])
    created = await create_task(
        client,
        task_board,
        tag_ids=[str(task_board.tag_b.id), str(task_board.tag_a.id)],
        assignee_id=str(users["developer_b"].id),
        story_points=3,
    )
    task = created["data"]
    task_id = task["id"]
    assert (task["key"], task["number"], task["version"]) == ("TASK-1", 1, 1)
    assert task["author_id"] == str(users["developer"].id)
    assert task["assignee_is_project_member"] is True
    assert task["tag_ids"] == sorted([str(task_board.tag_a.id), str(task_board.tag_b.id)])
    history = await task_history(client, task_id)
    assert [event["event_type"] for event in history] == ["task.created"]
    assert history[0]["actor_id"] == str(users["developer"].id)
    changes = {change["field"]: change for change in history[0]["changes"]}
    assert changes["title"]["old_value"] is None
    assert changes["title"]["new_value"] == task["title"]
    assert {tag["name"] for tag in changes["tag_ids"]["new_value"]} == {"API", "Release"}

    patched = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"expected_version": 1, "title": "Implement and verify", "priority": "high"},
    )
    assert patched.status_code == 200, patched.text
    updated = patched.json()
    assert updated["data"]["version"] == 2
    assert updated["board_revision"] == created["board_revision"] + 1
    history = await task_history(client, task_id)
    assert len(history) == 2
    assert history[-1]["event_type"] == "task.updated"
    assert {change["field"] for change in history[-1]["changes"]} == {"title", "priority"}
    assert history[0]["operation_id"] != history[1]["operation_id"]

    noop = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"expected_version": 2, "title": "Implement and verify", "priority": "high"},
    )
    assert noop.status_code == 200, noop.text
    assert noop.json() == updated
    assert await task_history(client, task_id) == history

    stale = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"expected_version": 1, "title": "Lost edit"}
    )
    assert stale.status_code == 409, stale.text
    assert await read_task(client, task_id) == updated
    assert await task_history(client, task_id) == history


async def test_move_respects_hidden_neighbors_and_does_not_version_them(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard
) -> None:
    await login(client, users["developer"])
    first = (await create_task(client, task_board, "First visible", priority="high"))["data"]
    hidden = (await create_task(client, task_board, "Hidden neighbor", priority="low"))["data"]
    anchor = (await create_task(client, task_board, "Second visible", priority="high"))["data"]
    moved = (await create_task(client, task_board, "Move me", priority="high"))["data"]
    visible = await client.get(
        f"/api/v1/boards/{task_board.board.id}/tasks", params={"priority": "high"}
    )
    assert [task["id"] for task in visible.json()["items"]] == [
        first["id"],
        anchor["id"],
        moved["id"],
    ]
    response = await client.post(
        f"/api/v1/tasks/{moved['id']}/move",
        json={
            "column_id": str(task_board.todo.id),
            "before_task_id": anchor["id"],
            "expected_version": 1,
        },
    )
    assert response.status_code == 200, response.text
    result = await client.get(f"/api/v1/boards/{task_board.board.id}/tasks")
    tasks = result.json()["items"]
    assert [task["id"] for task in tasks] == [first["id"], hidden["id"], moved["id"], anchor["id"]]
    assert [task["position"] for task in tasks] == [0, 1, 2, 3]
    assert [task["version"] for task in tasks] == [1, 1, 2, 1]
    assert len(await task_history(client, anchor["id"])) == 1
    assert len(await task_history(client, hidden["id"])) == 1

    noop = await client.post(
        f"/api/v1/tasks/{moved['id']}/move",
        json={
            "column_id": str(task_board.todo.id),
            "before_task_id": anchor["id"],
            "expected_version": 2,
        },
    )
    assert noop.status_code == 200, noop.text
    assert noop.json() == response.json()


@pytest.mark.parametrize("anchor_state", ["deleted", "other_column", "foreign"])
async def test_invalid_anchor_does_not_change_order_version_or_history(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard, anchor_state: str
) -> None:
    await login(client, users["developer"])
    moved = await create_task(client, task_board, "Stay in place")
    moved_id = moved["data"]["id"]
    if anchor_state == "foreign":
        await login(client, users["second_pm"])
        response = await client.post(
            f"/api/v1/boards/{task_board.foreign_column.board_id}/tasks",
            json={"title": "Private anchor", "column_id": str(task_board.foreign_column.id)},
        )
        assert response.status_code == 201, response.text
        anchor_id = response.json()["data"]["id"]
        await login(client, users["developer"])
    else:
        anchor = await create_task(client, task_board, "Obsolete anchor")
        anchor_id = anchor["data"]["id"]
        if anchor_state == "deleted":
            response = await client.delete(
                f"/api/v1/tasks/{anchor_id}", params={"expected_version": 1}
            )
        else:
            response = await client.post(
                f"/api/v1/tasks/{anchor_id}/move",
                json={
                    "column_id": str(task_board.doing.id),
                    "before_task_id": None,
                    "expected_version": 1,
                },
            )
        assert response.status_code == 200, response.text
    listing_path = f"/api/v1/boards/{task_board.board.id}/tasks"
    before_listing = (await client.get(listing_path)).json()
    before_task = await read_task(client, moved_id)
    before_history = await task_history(client, moved_id)
    rejected = await client.post(
        f"/api/v1/tasks/{moved_id}/move",
        json={
            "column_id": str(task_board.todo.id),
            "before_task_id": anchor_id,
            "expected_version": 1,
        },
    )
    expected = (
        (422, "INVALID_REFERENCE") if anchor_state == "foreign" else (409, "POSITION_CONFLICT")
    )
    assert rejected.status_code == expected[0], rejected.text
    assert rejected.json()["error"]["code"] == expected[1]
    assert (await client.get(listing_path)).json() == before_listing
    assert await read_task(client, moved_id) == before_task
    assert await task_history(client, moved_id) == before_history


async def test_completion_and_reopening_share_move_operation_and_preserve_lifecycle(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard
) -> None:
    await login(client, users["developer"])
    created = await create_task(client, task_board)
    task_id = created["data"]["id"]
    for version, column, completed, event_type in (
        (1, task_board.done, True, "task.completed"),
        (2, task_board.doing, False, "task.reopened"),
        (3, task_board.done, True, "task.completed"),
    ):
        response = await client.post(
            f"/api/v1/tasks/{task_id}/move",
            json={"column_id": str(column.id), "before_task_id": None, "expected_version": version},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["is_completed"] is completed
        assert response.json()["data"]["version"] == version + 1
        history = await task_history(client, task_id)
        latest_operation = [
            event for event in history if event["operation_id"] == history[-1]["operation_id"]
        ]
        assert {event["event_type"] for event in latest_operation} == {"task.moved", event_type}
        assert len({event["occurred_at"] for event in latest_operation}) == 1
    history = await task_history(client, task_id)
    assert sum(event["event_type"] == "task.completed" for event in history) == 2
    assert sum(event["event_type"] == "task.reopened" for event in history) == 1


async def test_create_in_done_has_one_completion_and_noop_does_not_repeat_it(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard
) -> None:
    await login(client, users["developer"])
    created = await create_task(client, task_board, column_id=str(task_board.done.id))
    task_id = created["data"]["id"]
    assert created["data"]["is_completed"] is True
    history = await task_history(client, task_id)
    assert {event["event_type"] for event in history} == {"task.created", "task.completed"}
    assert len({event["operation_id"] for event in history}) == 1
    response = await client.post(
        f"/api/v1/tasks/{task_id}/move",
        json={"column_id": str(task_board.done.id), "before_task_id": None, "expected_version": 1},
    )
    assert response.status_code == 200, response.text
    assert response.json() == created
    assert await task_history(client, task_id) == history


async def test_comment_and_soft_delete_preserve_history_but_hide_task_and_comments(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard, db: AsyncSession
) -> None:
    await login(client, users["developer"])
    created = await create_task(client, task_board)
    task_id = created["data"]["id"]
    comment = await client.post(
        f"/api/v1/tasks/{task_id}/comments", json={"text": "<script>plain text</script>"}
    )
    assert comment.status_code == 201, comment.text
    assert comment.json()["data"]["text"] == "<script>plain text</script>"
    assert comment.json()["board_revision"] == created["board_revision"] + 1
    assert (await read_task(client, task_id))["data"]["version"] == 1
    comment_events = await task_history(client, task_id)
    assert [event["event_type"] for event in comment_events] == ["task.created", "comment.created"]

    await login(client, users["developer_b"])
    forbidden = await client.delete(f"/api/v1/tasks/{task_id}", params={"expected_version": 1})
    assert forbidden.status_code == 403, forbidden.text
    assert (await read_task(client, task_id))["data"]["version"] == 1

    await login(client, users["pm"])
    deleted = await client.delete(f"/api/v1/tasks/{task_id}", params={"expected_version": 1})
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["data"] is None
    assert deleted.json()["board_revision"] == comment.json()["board_revision"] + 1
    history = await task_history(client, task_id)
    assert len(history) == 3
    assert history[-1]["event_type"] == "task.deleted"
    assert history[-1]["actor_id"] == str(users["pm"].id)
    assert (await client.get(f"/api/v1/tasks/{task_id}")).status_code == 404
    assert (await client.get(f"/api/v1/tasks/{task_id}/comments")).status_code == 404
    assert (
        await client.post(f"/api/v1/tasks/{task_id}/comments", json={"text": "Late comment"})
    ).status_code == 404
    listing = await client.get(f"/api/v1/boards/{task_board.board.id}/tasks")
    assert listing.json()["items"] == []
    assert listing.json()["total"] == 0
    stored = await db.scalar(select(Task).where(Task.id == UUID(task_id)))
    assert stored is not None and stored.deleted_at is not None
    next_task = await create_task(client, task_board, "Number is never reused")
    assert next_task["data"]["number"] == 2


async def test_filters_combine_all_tags_with_assignee_deadline_priority_column_and_search(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard
) -> None:
    await login(client, users["developer"])
    common = {
        "tag_ids": [str(task_board.tag_a.id), str(task_board.tag_b.id)],
        "assignee_id": str(users["developer_b"].id),
        "deadline": "2026-09-20",
        "priority": "high",
    }
    match = await create_task(client, task_board, "Release candidate", **common)
    for title, changes in (
        ("Release missing tag", {"tag_ids": [str(task_board.tag_a.id)]}),
        ("Release unassigned", {"assignee_id": None}),
        ("Release no deadline", {"deadline": None}),
        ("Release too late", {"deadline": "2026-09-21"}),
        ("Release low priority", {"priority": "low"}),
        ("Release in progress", {"column_id": str(task_board.doing.id)}),
        ("Unrelated title", {}),
    ):
        await create_task(client, task_board, title, **(common | changes))
    params = [
        ("tag_ids", str(task_board.tag_a.id)),
        ("tag_ids", str(task_board.tag_b.id)),
        ("assignee_id", str(users["developer_b"].id)),
        ("deadline_from", "2026-09-20"),
        ("deadline_to", "2026-09-20"),
        ("priority", "medium"),
        ("priority", "high"),
        ("column_ids", str(task_board.todo.id)),
        ("q", "RELEASE"),
    ]
    response = await client.get(f"/api/v1/boards/{task_board.board.id}/tasks", params=params)
    assert response.status_code == 200, response.text
    assert [task["id"] for task in response.json()["items"]] == [match["data"]["id"]]
    assert response.json()["total"] == 1
    by_key = await client.get(
        f"/api/v1/boards/{task_board.board.id}/tasks", params={"q": match["data"]["key"].lower()}
    )
    assert [task["id"] for task in by_key.json()["items"]] == [match["data"]["id"]]
    unassigned = await client.get(
        f"/api/v1/boards/{task_board.board.id}/tasks", params={"assignee_id": "unassigned"}
    )
    assert [task["title"] for task in unassigned.json()["items"]] == ["Release unassigned"]


async def test_removed_assignee_is_preserved_but_cannot_be_assigned_again(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard, db: AsyncSession
) -> None:
    await login(client, users["developer"])
    assignee_id = str(users["developer_b"].id)
    created = await create_task(client, task_board, assignee_id=assignee_id)
    task_id = created["data"]["id"]
    await db.execute(
        delete(ProjectMember).where(
            ProjectMember.project_id == task_board.project.id,
            ProjectMember.user_id == users["developer_b"].id,
        )
    )
    await db.commit()
    after_removal = await read_task(client, task_id)
    assert after_removal["data"]["assignee_id"] == assignee_id
    assert after_removal["data"]["assignee_is_project_member"] is False

    preserved = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"expected_version": 1, "title": "Keep former assignee", "assignee_id": assignee_id},
    )
    assert preserved.status_code == 200, preserved.text
    assert preserved.json()["data"]["version"] == 2
    assert preserved.json()["data"]["assignee_id"] == assignee_id
    assert preserved.json()["data"]["assignee_is_project_member"] is False
    updated_events = await task_history(client, task_id)
    assert {change["field"] for change in updated_events[-1]["changes"]} == {"title"}

    other = await create_task(client, task_board, "Unassigned task")
    other_id = other["data"]["id"]
    invalid = await client.patch(
        f"/api/v1/tasks/{other_id}",
        json={"expected_version": 1, "title": "Must not persist", "assignee_id": assignee_id},
    )
    assert invalid.status_code == 422, invalid.text
    assert invalid.json()["error"]["code"] == "INVALID_REFERENCE"
    assert await read_task(client, other_id) == other
    assert len(await task_history(client, other_id)) == 1

    unassigned = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"expected_version": 2, "assignee_id": None}
    )
    assert unassigned.status_code == 200, unassigned.text
    assert unassigned.json()["data"]["assignee_id"] is None
    assert unassigned.json()["data"]["version"] == 3
    history_before_retry = await task_history(client, task_id)
    reassigned = await client.patch(
        f"/api/v1/tasks/{task_id}", json={"expected_version": 3, "assignee_id": assignee_id}
    )
    assert reassigned.status_code == 422, reassigned.text
    assert reassigned.json()["error"]["code"] == "INVALID_REFERENCE"
    assert await read_task(client, task_id) == unassigned.json()
    assert await task_history(client, task_id) == history_before_retry


async def test_audit_keeps_reference_names_from_the_time_of_each_operation(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard, db: AsyncSession
) -> None:
    await login(client, users["developer"])
    assignee = users["developer_b"]
    original_names = {
        "column_id": task_board.todo.name,
        "assignee_id": assignee.name,
        "tag_ids": task_board.tag_a.name,
    }
    created = await create_task(
        client, task_board, assignee_id=str(assignee.id), tag_ids=[str(task_board.tag_a.id)]
    )
    task_id = created["data"]["id"]
    original_changes = (await task_history(client, task_id))[0]["changes"]
    creation = {change["field"]: change["new_value"] for change in original_changes}
    assert creation["column_id"]["name"] == original_names["column_id"]
    assert creation["assignee_id"]["name"] == original_names["assignee_id"]
    assert creation["tag_ids"][0]["name"] == original_names["tag_ids"]

    task_board.todo.name = "Renamed backlog"
    task_board.tag_a.name = "Renamed API tag"
    assignee.name = "Renamed colleague"
    await db.commit()
    assert (await task_history(client, task_id))[0]["changes"] == original_changes

    cleared = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"expected_version": 1, "assignee_id": None, "tag_ids": []},
    )
    assert cleared.status_code == 200, cleared.text
    updated = (await task_history(client, task_id))[-1]
    changes = {change["field"]: change for change in updated["changes"]}
    assert changes["assignee_id"]["old_value"] == {
        "id": str(assignee.id),
        "name": "Renamed colleague",
    }
    assert changes["assignee_id"]["new_value"] is None
    assert changes["tag_ids"]["old_value"] == [
        {"id": str(task_board.tag_a.id), "name": "Renamed API tag"}
    ]
    assert changes["tag_ids"]["new_value"] == []

    moved = await client.post(
        f"/api/v1/tasks/{task_id}/move",
        json={"expected_version": 2, "column_id": str(task_board.doing.id), "before_task_id": None},
    )
    assert moved.status_code == 200, moved.text
    moved_event = (await task_history(client, task_id))[-1]
    column_change = next(
        change for change in moved_event["changes"] if change["field"] == "column_id"
    )
    assert column_change["old_value"] == {"id": str(task_board.todo.id), "name": "Renamed backlog"}
    assert column_change["new_value"] == {
        "id": str(task_board.doing.id),
        "name": task_board.doing.name,
    }
    assert (await task_history(client, task_id))[0]["changes"] == original_changes


@pytest.mark.parametrize("invalid_field", ["column_id", "tag_ids", "assignee_id"])
async def test_invalid_references_fail_without_consuming_number_revision_or_audit(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard, invalid_field: str
) -> None:
    await login(client, users["developer"])
    foreign_values = {
        "column_id": str(task_board.foreign_column.id),
        "tag_ids": [str(task_board.foreign_tag.id)],
        "assignee_id": str(users["outsider"].id),
    }
    response = await client.post(
        f"/api/v1/boards/{task_board.board.id}/tasks",
        json={
            "title": "Must not be saved",
            "column_id": str(task_board.todo.id),
            invalid_field: foreign_values[invalid_field],
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "INVALID_REFERENCE"
    listing = await client.get(f"/api/v1/boards/{task_board.board.id}/tasks")
    assert listing.json()["total"] == 0
    assert listing.json()["board_revision"] == 0
    valid = await create_task(client, task_board)
    assert valid["data"]["number"] == 1
    assert valid["board_revision"] == 1
    assert len(await task_history(client, valid["data"]["id"])) == 1


@pytest.mark.parametrize("invalid_filter", ["column_ids", "tag_ids", "assignee_id"])
async def test_filters_reject_references_outside_the_project(
    client: AsyncClient, users: dict[str, User], task_board: TaskBoard, invalid_filter: str
) -> None:
    await login(client, users["developer"])
    values = {
        "column_ids": str(task_board.foreign_column.id),
        "tag_ids": str(task_board.foreign_tag.id),
        "assignee_id": str(users["outsider"].id),
    }
    response = await client.get(
        f"/api/v1/boards/{task_board.board.id}/tasks",
        params={invalid_filter: values[invalid_filter]},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "INVALID_REFERENCE"


async def test_simultaneous_edits_have_one_winner_and_no_lost_update(
    client: AsyncClient, app: FastAPI, users: dict[str, User], task_board: TaskBoard
) -> None:
    await login(client, users["developer"])
    created = await create_task(client, task_board)
    task_id = created["data"]["id"]
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url=client.base_url,
        cookies=client.cookies,
        headers=client.headers,
    ) as second_client:
        responses = await asyncio.gather(
            client.patch(
                f"/api/v1/tasks/{task_id}", json={"expected_version": 1, "title": "First edit"}
            ),
            second_client.patch(
                f"/api/v1/tasks/{task_id}", json={"expected_version": 1, "title": "Second edit"}
            ),
        )
    assert sorted(response.status_code for response in responses) == [200, 409]
    winning = next(response.json() for response in responses if response.status_code == 200)
    assert (await read_task(client, task_id)) == winning
    assert winning["data"]["version"] == 2
    assert winning["board_revision"] == created["board_revision"] + 1
    assert len(await task_history(client, task_id)) == 2
