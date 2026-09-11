"""Project boundaries and container invariants against the real PostgreSQL API."""

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response

from app.db.domain import User
from tests.support import login

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

Json = dict[str, Any]


def payload(response: Response, status: int = 200) -> Json:
    assert response.status_code == status, response.text
    return response.json()


def error(response: Response, status: int, code: str) -> None:
    body = payload(response, status)
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["details"], list)
    assert body["error"]["request_id"]


async def project(client: AsyncClient, key: str = "TEAM") -> Json:
    return payload(
        await client.post("/api/v1/projects", json={"key": key, "name": "Командный проект"}),
        201,
    )


async def board(client: AsyncClient, project_id: str) -> Json:
    created = payload(
        await client.post(f"/api/v1/projects/{project_id}/boards", json={"name": "Разработка"}),
        201,
    )
    return payload(await client.get(f"/api/v1/boards/{created['id']}"))


async def test_project_creation_global_roles_and_owner_membership(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["developer"])
    error(
        await client.post("/api/v1/projects", json={"key": "DEV", "name": "Запрещено"}),
        403,
        "FORBIDDEN",
    )
    await login(client, users["pm"])
    created = payload(
        await client.post(
            "/api/v1/projects",
            json={"key": "team", "name": "  Команда  ", "timezone": "Asia/Yekaterinburg"},
        ),
        201,
    )
    assert created["key"] == "TEAM"
    assert created["name"] == "Команда"
    assert created["owner_id"] == str(users["pm"].id)
    assert created["member_count"] == 1
    assert created["board_count"] == 0
    members = payload(await client.get(f"/api/v1/projects/{created['id']}/members"))
    assert members["total"] == 1
    assert members["items"][0]["is_owner"] is True
    assert members["items"][0]["user_id"] == created["owner_id"]
    assert payload(await client.get(f"/api/v1/projects/{created['id']}/boards"))["items"] == []
    error(
        await client.post("/api/v1/projects", json={"key": "TEAM", "name": "Дубль"}),
        409,
        "DUPLICATE_KEY",
    )
    await login(client, users["outsider"])
    assert payload(await client.get("/api/v1/projects"))["total"] == 0
    error(await client.get(f"/api/v1/projects/{created['id']}"), 404, "NOT_FOUND")
    await login(client, users["admin"])
    assert payload(await client.get(f"/api/v1/projects/{created['id']}"))["id"] == created["id"]
    assert payload(await client.get("/api/v1/projects"))["total"] == 1
    assert (await project(client, "ADMIN"))["owner_id"] == str(users["admin"].id)


async def test_membership_idempotence_and_transfer_to_developer(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    base = f"/api/v1/projects/{created['id']}"
    member = payload(
        await client.post(f"{base}/members", json={"email": users["developer"].email}), 201
    )
    repeated = payload(
        await client.post(f"{base}/members", json={"email": users["developer"].email})
    )
    assert repeated == member
    error(
        await client.post(f"{base}/members", json={"email": "unregistered@example.com"}),
        422,
        "INVALID_REFERENCE",
    )
    error(await client.delete(f"{base}/members/{users['pm'].id}"), 409, "OWNER_REQUIRED")
    error(
        await client.put(f"{base}/owner", json={"user_id": str(users["outsider"].id)}),
        422,
        "INVALID_REFERENCE",
    )
    transferred = payload(
        await client.put(f"{base}/owner", json={"user_id": str(users["developer"].id)})
    )
    assert transferred["owner_id"] == str(users["developer"].id)
    members = payload(await client.get(f"{base}/members"))
    assert members["total"] == 2
    assert {entry["user_id"] for entry in members["items"]} == {
        str(users["pm"].id),
        str(users["developer"].id),
    }
    error(await client.patch(base, json={"name": "Нет прав владельца"}), 403, "FORBIDDEN")
    await login(client, users["developer"])
    assert payload(await client.patch(base, json={"name": "Новый владелец"}))["name"] == (
        "Новый владелец"
    )
    for _ in range(2):
        response = await client.delete(f"{base}/members/{users['pm'].id}")
        assert response.status_code == 204, response.text
        assert response.content == b""
    error(await client.delete(f"{base}/members/{users['developer'].id}"), 409, "OWNER_REQUIRED")


async def test_outsider_cannot_read_or_mutate_nested_resources(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    snapshot = await board(client, created["id"])
    tag = payload(
        await client.post(f"/api/v1/projects/{created['id']}/tags", json={"name": "Backend"}),
        201,
    )
    base = f"/api/v1/projects/{created['id']}"
    board_path = f"/api/v1/boards/{snapshot['board']['id']}"
    column_path = f"/api/v1/columns/{snapshot['columns'][0]['id']}"
    tag_path = f"/api/v1/tags/{tag['id']}"
    await login(client, users["second_pm"])
    for path in (base, f"{base}/members", f"{base}/boards", f"{base}/tags", board_path):
        error(await client.get(path), 404, "NOT_FOUND")
    for path in (base, board_path, column_path, tag_path):
        error(await client.patch(path, json={"name": "Недоступно"}), 404, "NOT_FOUND")
        error(await client.delete(path), 404, "NOT_FOUND")
    error(await client.post(f"{base}/boards", json={"name": "Недоступно"}), 404, "NOT_FOUND")
    error(await client.post(f"{base}/tags", json={"name": "Недоступно"}), 404, "NOT_FOUND")
    error(
        await client.post(f"{base}/members", json={"email": users["outsider"].email}),
        404,
        "NOT_FOUND",
    )
    error(await client.delete(f"{base}/members/{users['pm'].id}"), 404, "NOT_FOUND")
    error(
        await client.put(f"{base}/owner", json={"user_id": str(users["second_pm"].id)}),
        404,
        "NOT_FOUND",
    )
    error(
        await client.post(f"{board_path}/columns", json={"name": "X", "category": "todo"}),
        404,
        "NOT_FOUND",
    )
    error(
        await client.put(
            f"{board_path}/columns/order",
            json={
                "column_ids": [entry["id"] for entry in snapshot["columns"]],
                "expected_revision": snapshot["revision"],
            },
        ),
        404,
        "NOT_FOUND",
    )
    error(await client.get(f"/api/v1/boards/{uuid4()}"), 404, "NOT_FOUND")


async def test_default_columns_noop_and_position_compaction(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    snapshot = await board(client, created["id"])
    path = f"/api/v1/boards/{snapshot['board']['id']}"
    assert [
        (entry["name"], entry["category"], entry["position"]) for entry in snapshot["columns"]
    ] == [
        ("К выполнению", "todo", 0),
        ("В работе", "in_progress", 1),
        ("Готово", "done", 2),
    ]
    assert snapshot["tasks"] == []
    original_revision = snapshot["revision"]
    renamed = payload(await client.patch(path, json={"name": snapshot["board"]["name"]}))
    assert renamed["board_revision"] == original_revision
    first_column = snapshot["columns"][0]
    renamed_column = payload(
        await client.patch(
            f"/api/v1/columns/{first_column['id']}", json={"name": first_column["name"]}
        )
    )
    assert renamed_column["board_revision"] == original_revision
    reordered = payload(
        await client.put(
            f"{path}/columns/order",
            json={
                "column_ids": [entry["id"] for entry in snapshot["columns"]],
                "expected_revision": original_revision,
            },
        )
    )
    assert reordered["board_revision"] == original_revision
    added = payload(
        await client.post(f"{path}/columns", json={"name": "Проверка", "category": "in_progress"}),
        201,
    )
    assert added["data"]["position"] == 3
    assert added["board_revision"] == original_revision + 1
    response = await client.delete(f"/api/v1/columns/{snapshot['columns'][1]['id']}")
    assert response.status_code == 204, response.text
    current = payload(await client.get(path))
    assert current["revision"] == added["board_revision"] + 1
    assert [entry["position"] for entry in current["columns"]] == [0, 1, 2]
    assert current["columns"][-1]["id"] == added["data"]["id"]


async def test_column_order_rejects_incomplete_duplicate_foreign_and_stale_ids(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    snapshot = await board(client, created["id"])
    second = await board(client, created["id"])
    path = f"/api/v1/boards/{snapshot['board']['id']}"
    snapshot = payload(await client.get(path))
    ids = [entry["id"] for entry in snapshot["columns"]]
    original_revision = snapshot["revision"]
    invalid_orders = [ids[:-1], [ids[0], ids[0], ids[2]], [*ids[:-1], second["columns"][0]["id"]]]
    for invalid in invalid_orders:
        response = await client.put(
            f"{path}/columns/order",
            json={"column_ids": invalid, "expected_revision": original_revision},
        )
        assert response.status_code == 422, response.text
        unchanged = payload(await client.get(path))
        assert unchanged["revision"] == original_revision
        assert [entry["id"] for entry in unchanged["columns"]] == ids
    result = payload(
        await client.put(
            f"{path}/columns/order",
            json={"column_ids": ids[::-1], "expected_revision": original_revision},
        )
    )
    assert result["board_revision"] == original_revision + 1
    assert [entry["id"] for entry in result["data"]] == ids[::-1]
    assert [entry["position"] for entry in result["data"]] == [0, 1, 2]
    error(
        await client.put(
            f"{path}/columns/order",
            json={"column_ids": ids, "expected_revision": original_revision},
        ),
        409,
        "VERSION_CONFLICT",
    )
    current = payload(await client.get(path))
    assert current["revision"] == result["board_revision"]
    assert [entry["id"] for entry in current["columns"]] == ids[::-1]


async def test_only_empty_containers_can_be_deleted(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    base = f"/api/v1/projects/{created['id']}"
    tag = payload(await client.post(f"{base}/tags", json={"name": "Релиз"}), 201)
    error(await client.delete(base), 409, "PROJECT_NOT_EMPTY")
    assert (await client.delete(f"/api/v1/tags/{tag['id']}")).status_code == 204
    snapshot = await board(client, created["id"])
    path = f"/api/v1/boards/{snapshot['board']['id']}"
    error(await client.delete(base), 409, "PROJECT_NOT_EMPTY")
    error(await client.delete(path), 409, "BOARD_NOT_EMPTY")
    for column in snapshot["columns"]:
        response = await client.delete(f"/api/v1/columns/{column['id']}")
        assert response.status_code == 204, response.text
    response = await client.delete(path)
    assert response.status_code == 204, response.text
    response = await client.delete(base)
    assert response.status_code == 204, response.text
    assert response.content == b""
    error(await client.get(base), 404, "NOT_FOUND")
    assert payload(await client.get("/api/v1/projects"))["total"] == 0


async def test_tag_permissions_case_insensitive_duplicates_and_noop(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    base = f"/api/v1/projects/{created['id']}"
    payload(await client.post(f"{base}/members", json={"email": users["developer"].email}), 201)
    snapshot = await board(client, created["id"])
    board_path = f"/api/v1/boards/{snapshot['board']['id']}"
    await login(client, users["developer"])
    tag = payload(await client.post(f"{base}/tags", json={"name": "  Backend  "}), 201)
    assert tag["name"] == "Backend"
    assert tag["color"] == "#64748B"
    path = f"/api/v1/tags/{tag['id']}"
    error(await client.post(f"{base}/tags", json={"name": "backend"}), 409, "DUPLICATE_TAG")
    error(await client.patch(path, json={"name": "Новое имя"}), 403, "FORBIDDEN")
    error(await client.delete(path), 403, "FORBIDDEN")
    await login(client, users["pm"])
    revision = payload(await client.get(board_path))["revision"]
    assert (
        payload(await client.patch(path, json={"name": tag["name"], "color": tag["color"]})) == tag
    )
    assert payload(await client.get(board_path))["revision"] == revision
    other = payload(await client.post(f"{base}/tags", json={"name": "Frontend"}), 201)
    error(
        await client.patch(f"/api/v1/tags/{other['id']}", json={"name": "BACKEND"}),
        409,
        "DUPLICATE_TAG",
    )
    names = [entry["name"] for entry in payload(await client.get(f"{base}/tags"))["items"]]
    assert names == ["Backend", "Frontend"]


async def test_deleted_task_still_protects_column_and_tag_history(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    snapshot = await board(client, created["id"])
    tag = payload(
        await client.post(f"/api/v1/projects/{created['id']}/tags", json={"name": "История"}),
        201,
    )
    board_path = f"/api/v1/boards/{snapshot['board']['id']}"
    column_path = f"/api/v1/columns/{snapshot['columns'][0]['id']}"
    task = payload(
        await client.post(
            f"{board_path}/tasks",
            json={
                "title": "Сохранить историю",
                "column_id": snapshot["columns"][0]["id"],
                "tag_ids": [tag["id"]],
            },
        ),
        201,
    )["data"]
    for delete_task in (True, False):
        error(await client.delete(column_path), 409, "COLUMN_NOT_EMPTY")
        error(await client.delete(f"/api/v1/tags/{tag['id']}"), 409, "TAG_IN_USE")
        if delete_task:
            payload(
                await client.delete(
                    f"/api/v1/tasks/{task['id']}", params={"expected_version": task["version"]}
                )
            )
    assert payload(await client.get(board_path))["tasks"] == []
    history = payload(await client.get(f"/api/v1/tasks/{task['id']}/history"))
    assert history["total"] >= 2
    error(await client.get(f"/api/v1/tasks/{task['id']}"), 404, "NOT_FOUND")


async def test_project_changes_advance_every_board_and_noops_do_not(
    client: AsyncClient, users: dict[str, User]
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    base = f"/api/v1/projects/{created['id']}"
    first = await board(client, created["id"])
    first_path = f"/api/v1/boards/{first['board']['id']}"
    second = await board(client, created["id"])
    second_path = f"/api/v1/boards/{second['board']['id']}"
    updated_first = payload(await client.get(first_path))
    assert updated_first["revision"] == first["revision"] + 1
    assert updated_first["project"]["board_count"] == 2
    revisions = [updated_first["revision"], second["revision"]]

    payload(await client.patch(base, json={"description": "Новый контекст для всех досок"}))
    for path, revision in zip((first_path, second_path), revisions, strict=True):
        snapshot = payload(await client.get(path))
        assert snapshot["revision"] == revision + 1
        assert snapshot["project"]["description"] == "Новый контекст для всех досок"
    # A repeated field value and repeated existing member do not advance revisions.
    payload(await client.patch(base, json={"description": "Новый контекст для всех досок"}))
    payload(await client.post(f"{base}/members", json={"email": users["pm"].email}))
    for path, revision in zip((first_path, second_path), revisions, strict=True):
        assert payload(await client.get(path))["revision"] == revision + 1

    payload(await client.post(f"{base}/members", json={"email": users["developer"].email}), 201)
    for path, revision in zip((first_path, second_path), revisions, strict=True):
        snapshot = payload(await client.get(path))
        assert snapshot["revision"] == revision + 2
        assert snapshot["project"]["member_count"] == 2
    assert (await client.delete(f"{base}/members/{users['developer'].id}")).status_code == 204
    for path, revision in zip((first_path, second_path), revisions, strict=True):
        assert payload(await client.get(path))["revision"] == revision + 3

    # Removing an empty board changes the remaining board's project DTO and revision.
    for column in second["columns"]:
        assert (await client.delete(f"/api/v1/columns/{column['id']}")).status_code == 204
    assert (await client.delete(second_path)).status_code == 204
    remaining = payload(await client.get(first_path))
    assert remaining["revision"] == revisions[0] + 4
    assert remaining["project"]["board_count"] == 1
    assert remaining["project"]["member_count"] == 1
    error(await client.get(second_path), 404, "NOT_FOUND")


async def test_committed_member_removal_survives_socket_revalidation_failure(
    client: AsyncClient,
    app: FastAPI,
    users: dict[str, User],
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    await login(client, users["pm"])
    created = await project(client)
    base = f"/api/v1/projects/{created['id']}"
    payload(await client.post(f"{base}/members", json={"email": users["developer"].email}), 201)

    async def fail_revalidation(user_id: UUID) -> None:
        raise RuntimeError("private-socket-connection-detail")

    monkeypatch.setattr(app.state.event_hub, "revalidate_user", fail_revalidation)
    response = await client.delete(f"{base}/members/{users['developer'].id}")
    assert response.status_code == 204, response.text
    members = payload(await client.get(f"{base}/members"))
    assert members["total"] == 1
    assert members["items"][0]["user_id"] == str(users["pm"].id)
    assert "membership_socket_revalidation_failed" in caplog.text
    assert "private-socket-connection-detail" not in caplog.text
