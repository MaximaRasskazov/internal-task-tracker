"""A complete API workflow across authentication, ownership, tasks, history, and analytics."""

from datetime import UTC, datetime
from typing import Any

import pytest
from httpx import AsyncClient, Response

from app.db.domain import User
from tests.support import login

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def payload(response: Response, status: int = 200) -> dict[str, Any]:
    assert response.status_code == status, response.text
    assert response.headers["x-request-id"]
    return response.json()


async def test_project_lifecycle_across_backend_modules(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    project = payload(
        await client.post(
            "/api/v1/projects",
            json={"key": "ACCEPT", "name": "Сквозная приемка", "timezone": "UTC"},
        ),
        201,
    )
    project_path = f"/api/v1/projects/{project['id']}"
    for key in ("developer", "developer_b"):
        payload(await client.post(f"{project_path}/members", json={"email": users[key].email}), 201)
    board = payload(
        await client.post(f"{project_path}/boards", json={"name": "Выпуск продукта"}), 201
    )
    board_path = f"/api/v1/boards/{board['id']}"
    snapshot = payload(await client.get(board_path))
    todo = next(column for column in snapshot["columns"] if column["category"] == "todo")
    done = next(column for column in snapshot["columns"] if column["category"] == "done")
    review = payload(
        await client.post(
            f"{board_path}/columns", json={"name": "Согласование", "category": "in_progress"}
        ),
        201,
    )["data"]
    tags = [
        payload(await client.post(f"{project_path}/tags", json={"name": name}), 201)
        for name in ("Backend", "Приемка")
    ]
    today = datetime.now(UTC).date().isoformat()
    created = payload(
        await client.post(
            f"{board_path}/tasks",
            json={
                "title": "Проверить реальный сценарий команды",
                "description": "Запись создана автоматическим приемочным тестом.",
                "column_id": todo["id"],
                "priority": "high",
                "assignee_id": str(users["developer"].id),
                "deadline": today,
                "story_points": 3,
                "tag_ids": [tag["id"] for tag in tags],
            },
        ),
        201,
    )
    task = created["data"]
    task_path = f"/api/v1/tasks/{task['id']}"
    assert task["key"] == "ACCEPT-1"
    assert task["author_id"] == str(users["pm"].id)
    assert task["assignee_is_project_member"] is True

    # A distinct team member can continue the owner's task with server-generated identity.
    await login(client, users["developer"])
    comment = payload(
        await client.post(f"{task_path}/comments", json={"text": "Проверено участником команды"}),
        201,
    )
    assert comment["data"]["author_id"] == str(users["developer"].id)
    assert payload(await client.get(task_path))["data"]["version"] == task["version"]
    moved = payload(
        await client.post(
            f"{task_path}/move",
            json={
                "column_id": review["id"],
                "before_task_id": None,
                "expected_version": task["version"],
            },
        )
    )
    assert moved["board_revision"] > comment["board_revision"] > created["board_revision"]
    assert moved["data"]["version"] == task["version"] + 1

    # Combining independent filters preserves the saved board and task ordering.
    params = [
        ("assignee_id", str(users["developer"].id)),
        ("priority", "high"),
        ("tag_ids", tags[0]["id"]),
        ("tag_ids", tags[1]["id"]),
        ("deadline_from", today),
        ("deadline_to", today),
    ]
    filtered = payload(await client.get(f"{board_path}/tasks", params=params))
    assert [item["id"] for item in filtered["items"]] == [task["id"]]
    assert filtered["board_revision"] == moved["board_revision"]
    current = payload(await client.get(board_path))
    assert current["revision"] == moved["board_revision"]
    assert current["tasks"][0]["column_id"] == review["id"]

    completed = payload(
        await client.post(
            f"{task_path}/move",
            json={
                "column_id": done["id"],
                "before_task_id": None,
                "expected_version": moved["data"]["version"],
            },
        )
    )
    assert completed["data"]["is_completed"] is True
    analytics = payload(await client.get(f"{project_path}/analytics", params={"period": "week"}))
    assert analytics["timezone"] == "UTC"
    assert len(analytics["completion_over_time"]) == 7
    assert sum(point["completed_count"] for point in analytics["completion_over_time"]) == 1
    assert sum(column["count"] for column in analytics["status_distribution"]) == 1
    assert (
        next(
            column
            for column in analytics["status_distribution"]
            if column["column_id"] == done["id"]
        )["count"]
        == 1
    )
    history = payload(await client.get(f"{task_path}/history"))
    assert {event["event_type"] for event in history["items"]} >= {
        "task.created",
        "task.moved",
        "task.completed",
    }
    assert all(
        event["actor_id"] in {str(users["pm"].id), str(users["developer"].id)}
        for event in history["items"]
    )

    # Removing membership affects every read surface immediately, including historical data.
    await login(client, users["pm"])
    removed = await client.delete(f"{project_path}/members/{users['developer'].id}")
    assert removed.status_code == 204, removed.text
    await login(client, users["developer"])
    assert payload(await client.get("/api/v1/projects"))["total"] == 0
    for path in (
        project_path,
        board_path,
        task_path,
        f"{task_path}/history",
        f"{task_path}/comments",
        f"{project_path}/analytics",
    ):
        denied = await client.get(path)
        assert denied.status_code == 404, denied.text
        assert denied.json()["error"]["code"] == "NOT_FOUND"

    # The other member retains access; the former assignment is preserved and labelled.
    await login(client, users["developer_b"])
    task_after_removal = payload(await client.get(task_path))["data"]
    assert task_after_removal["assignee_id"] == str(users["developer"].id)
    assert task_after_removal["assignee_is_project_member"] is False
    assert payload(await client.get(f"{task_path}/comments"))["total"] == 1
