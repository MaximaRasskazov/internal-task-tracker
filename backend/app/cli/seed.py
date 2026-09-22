"""Explicit, non-destructive demonstration data for local, demo, and test databases."""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid5

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import hash_password
from app.db.domain import Board, Column, Project, ProjectMember, Tag, User
from app.db.session import Database
from app.schemas.domain import CommentCreate, Priority, TaskCreate, TaskDto, TaskMove, TaskPatch
from app.services.tasks import create_comment, create_task, move_task, update_task

SEED_NAMESPACE = UUID("d3b5f103-0848-411d-955b-6aa6a0f70b62")
SEED_LOCK = 6141942040271331
DEMO_USERS = (
    ("admin", "Демо: администратор", "admin"),
    ("pm", "Демо: руководитель команды", "pm"),
    ("dev-a", "Демо: разработчик А", "developer"),
    ("dev-b", "Демо: разработчик Б", "developer"),
    ("outsider", "Демо: другая команда", "developer"),
    ("pm-private", "Демо: руководитель PRIVATE", "pm"),
)


class SeedError(RuntimeError):
    """A safe, public-facing reason why the seed cannot continue."""


@dataclass(frozen=True)
class SeedSummary:
    created_users: int
    created_projects: int
    created_tasks: int
    preserved_existing_dataset: bool


def seed_id(identity: str) -> UUID:
    return uuid5(SEED_NAMESPACE, identity)


def validate_seed_settings(settings: Settings) -> None:
    if settings.app_env not in {"local", "demo", "test"}:
        raise SeedError("Demo seed is allowed only in APP_ENV=local, demo, or test.")
    if settings.demo_password is None or len(settings.demo_password.get_secret_value()) < 12:
        raise SeedError("DEMO_PASSWORD must be configured with at least 12 characters.")


async def _ensure_users(
    session: AsyncSession, settings: Settings, created_at: datetime
) -> tuple[dict[str, User], int]:
    assert settings.demo_password is not None
    users: dict[str, User] = {}
    created = 0
    for handle, name, role in DEMO_USERS:
        email = f"{handle}@example.test"
        identity = seed_id(f"user:{handle}")
        existing = await session.scalar(select(User).where(User.email == email))
        if existing is not None:
            if existing.id != identity:
                raise SeedError(f"Account {email} already exists outside this demo dataset.")
            users[handle] = existing
            continue
        if await session.get(User, identity) is not None:
            raise SeedError(
                "A demo account identity has been modified; existing data is preserved."
            )
        user = User(
            id=identity,
            name=name,
            email=email,
            password_hash=await asyncio.to_thread(
                hash_password, settings.demo_password.get_secret_value()
            ),
            role_code=role,
            created_at=created_at,
        )
        session.add(user)
        users[handle] = user
        created += 1
    await session.flush()
    return users, created


async def _existing_dataset(session: AsyncSession) -> bool:
    projects = list(
        await session.scalars(
            select(Project).where(
                (Project.key.in_(("TEAM", "PRIVATE")))
                | (Project.id.in_((seed_id("project:TEAM"), seed_id("project:PRIVATE"))))
            )
        )
    )
    for project in projects:
        if project.key not in {"TEAM", "PRIVATE"} or project.id != seed_id(
            f"project:{project.key}"
        ):
            raise SeedError("TEAM/PRIVATE is already in use outside this demo dataset.")
    if len(projects) == 1:
        raise SeedError("The existing demo dataset is incomplete; no existing data was changed.")
    return len(projects) == 2


@dataclass(frozen=True)
class SeedBoard:
    board: Board
    columns: dict[str, Column]


async def _create_board(
    session: AsyncSession, project: Project, slug: str, name: str, created_at: datetime
) -> SeedBoard:
    board = Board(
        id=seed_id(f"board:{slug}"),
        project_id=project.id,
        name=name,
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(board)
    await session.flush()
    columns: dict[str, Column] = {}
    for position, (key, title, category) in enumerate(
        (
            ("todo", "К выполнению", "todo"),
            ("in_progress", "В работе", "in_progress"),
            ("review", "Проверка командой", "in_progress"),
            ("done", "Готово", "done"),
        )
    ):
        column = Column(
            id=seed_id(f"column:{slug}:{key}"),
            board_id=board.id,
            name=title,
            category=category,
            position=position,
            created_at=created_at,
        )
        session.add(column)
        columns[key] = column
    await session.flush()
    return SeedBoard(board, columns)


async def _create_project(
    session: AsyncSession,
    key: str,
    name: str,
    owner: User,
    members: list[User],
    created_at: datetime,
) -> Project:
    if owner.role_code not in {"pm", "admin"} or not owner.is_active:
        raise SeedError("An existing demo owner no longer has an active PM/admin role.")
    project = Project(
        id=seed_id(f"project:{key}"),
        key=key,
        name=name,
        description="Демонстрационные записи для обучения и проверки приложения.",
        owner_id=owner.id,
        timezone="Asia/Yekaterinburg",
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(project)
    await session.flush()
    session.add_all(
        ProjectMember(project_id=project.id, user_id=user.id, joined_at=created_at)
        for user in [owner, *members]
    )
    await session.flush()
    return project


async def _create_tasks(
    session: AsyncSession,
    users: dict[str, User],
    delivery: SeedBoard,
    operations: SeedBoard,
    private_board: SeedBoard,
    tags: list[Tag],
    reference_date: date,
) -> None:
    titles = (
        "Настроить рабочее окружение",
        "Проверить авторизацию и роли",
        "Спроектировать таблицы проекта",
        "Проверить повторное завершение задачи",
        "Согласовать API с командой",
        "Подготовить карточку задачи",
        "Настроить поиск и фильтры",
        "Проверить сохранение порядка карточек",
        "Вернуть задачу на доработку",
        "Проверить мобильную доску",
        "Обсудить приоритеты следующей недели",
        "Добавить понятные сообщения об ошибках",
        "Протестировать доступ к закрытому проекту",
        "Повторно проверить сценарий приемки",
        "Проверить историю изменений",
        "Подготовить страницу аналитики",
        "Собрать мини-отчет по базе данных",
        "Обновить инструкцию запуска",
        "Проверить материалы демонстрации",
        "Провести командное ревью",
    )
    priorities: tuple[Priority, ...] = ("low", "medium", "high")
    assignees = (users["dev-a"].id, users["dev-b"].id, None)
    story_points = (None, 0, 1, 2, 3, 5, 8)
    deadlines = (
        None,
        reference_date - timedelta(days=2),
        reference_date,
        reference_date + timedelta(days=3),
        reference_date + timedelta(days=7),
    )
    tasks: list[tuple[SeedBoard, TaskDto]] = []

    def at(days_ago: int, offset: int = 0) -> datetime:
        return datetime.combine(
            reference_date - timedelta(days=days_ago), time(8), UTC
        ) + timedelta(minutes=offset * 10)

    for index, title in enumerate(titles):
        board = delivery if index < 16 else operations
        selected_tags = [] if index % 4 == 0 else [tags[index % 2].id]
        if index % 4 == 3:
            selected_tags.append(tags[2].id)
        result, _events = await create_task(
            session,
            board.board.id,
            users["pm"].id,
            TaskCreate(
                title=f"[Демо] {title}",
                description=(
                    "Демонстрационная запись. История создана учебным seed-сценарием "
                    "с управляемым временем; это не действия реальных участников."
                ),
                column_id=board.columns["todo"].id,
                priority=priorities[index % len(priorities)],
                assignee_id=assignees[index % len(assignees)],
                deadline=deadlines[index % len(deadlines)],
                story_points=story_points[index % len(story_points)],
                tag_ids=selected_tags,
            ),
            now=at(14, index),
        )
        tasks.append((board, result.data))

    for index, (_board, task) in enumerate(tasks[:6]):
        await create_comment(
            session,
            task.id,
            users["dev-a" if index % 2 == 0 else "dev-b"].id,
            CommentCreate(text="Демо-комментарий: согласовали проверку результата с командой."),
            now=at(10, index),
        )

    async def move(index: int, destination: str, days_ago: int) -> None:
        board, task = tasks[index]
        result, _events = await move_task(
            session,
            task.id,
            users["pm"].id,
            TaskMove(
                column_id=board.columns[destination].id,
                before_task_id=None,
                expected_version=task.version,
            ),
            now=at(days_ago, index),
        )
        tasks[index] = (board, result.data)

    for index in range(len(tasks)):
        if index % 5:
            await move(index, "review" if index % 5 == 4 else "in_progress", 8)
    board, task = tasks[1]
    result, _events = await update_task(
        session,
        task.id,
        users["pm"].id,
        TaskPatch(expected_version=task.version, priority="high", story_points=3),
        now=at(7),
    )
    tasks[1] = (board, result.data)
    for index in range(len(tasks)):
        if index % 5 in {2, 3}:
            await move(index, "done", 5)
    for index in range(len(tasks)):
        if index % 5 == 3:
            await move(index, "in_progress", 3)
    for index in range(len(tasks)):
        if index % 5 == 3:
            await move(index, "done", 1)

    for index in range(2):
        await create_task(
            session,
            private_board.board.id,
            users["pm-private"].id,
            TaskCreate(
                title=f"[Демо] Закрытая задача другой команды {index + 1}",
                description="Демонстрационная запись для проверки изоляции проектов.",
                column_id=private_board.columns["todo"].id,
                assignee_id=users["outsider"].id,
                priority="medium",
            ),
            now=at(14, index),
        )


async def seed_data(session: AsyncSession, settings: Settings, reference_date: date) -> SeedSummary:
    """Stage an atomic seed; the caller commits, or rolls back on any error.

    The stable project identities mark the entire dataset. A rerun preserves user edits,
    deletions, roles, passwords, and historical dates instead of resetting a live demo.
    """
    validate_seed_settings(settings)
    await session.execute(
        text("SELECT pg_advisory_xact_lock(:seed_lock)"), {"seed_lock": SEED_LOCK}
    )
    existing = await _existing_dataset(session)
    created_at = datetime.combine(reference_date - timedelta(days=30), time(8), UTC)
    users, created_users = await _ensure_users(session, settings, created_at)
    if existing:
        return SeedSummary(created_users, 0, 0, True)

    team = await _create_project(
        session,
        "TEAM",
        "Демо: внутренняя разработка",
        users["pm"],
        [users["dev-a"], users["dev-b"]],
        created_at,
    )
    private = await _create_project(
        session,
        "PRIVATE",
        "Демо: закрытый проект другой команды",
        users["pm-private"],
        [users["outsider"]],
        created_at,
    )
    delivery = await _create_board(
        session, team, "team-delivery", "Разработка продукта", created_at
    )
    operations = await _create_board(session, team, "team-operations", "Работа команды", created_at)
    private_board = await _create_board(session, private, "private", "Закрытая доска", created_at)
    tags = [
        Tag(id=seed_id("tag:backend"), project_id=team.id, name="Backend", color="#2563EB"),
        Tag(id=seed_id("tag:frontend"), project_id=team.id, name="Frontend", color="#7C3AED"),
        Tag(id=seed_id("tag:important"), project_id=team.id, name="Важно", color="#DC2626"),
    ]
    session.add_all(tags)
    await session.flush()
    await _create_tasks(session, users, delivery, operations, private_board, tags, reference_date)
    return SeedSummary(created_users, 2, 22, False)


async def seed_database(settings: Settings, reference_date: date) -> SeedSummary:
    validate_seed_settings(settings)
    database = Database(settings)
    if database.sessions is None:
        raise SeedError("DATABASE_URL must be configured before running the demo seed.")
    try:
        async with database.sessions() as session, session.begin():
            return await seed_data(session, settings, reference_date)
    finally:
        await database.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create or preserve the local demonstration dataset"
    )
    parser.add_argument("--reference-date", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    try:
        summary = asyncio.run(seed_database(Settings(), args.reference_date))
    except SeedError as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
    except Exception:
        # Database/configuration exceptions may embed connection credentials or input values.
        print("Seed failed. Check local configuration and apply migrations first.", file=sys.stderr)
        raise SystemExit(1) from None
    if summary.preserved_existing_dataset:
        print("Preserved existing demonstration data, passwords, roles, and historical dates.")
    else:
        print(
            f"Created demonstration data: {summary.created_users} users, "
            f"{summary.created_projects} projects, {summary.created_tasks} tasks."
        )
    print(
        "Demo sign-in emails are documented in product_spec.md §15. Secret values are not printed."
    )


if __name__ == "__main__":
    main()
