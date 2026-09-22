"""Explicit public projections; task and list projections perform bounded batch queries."""

from collections import defaultdict
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.domain import (
    AuditEvent,
    Board,
    Column,
    Comment,
    Project,
    ProjectMember,
    Tag,
    Task,
    TaskTag,
    User,
)
from app.schemas.domain import (
    AuditDto,
    BoardDto,
    ColumnDto,
    CommentDto,
    MemberDto,
    Person,
    ProjectDto,
    TagDto,
    TaskDto,
    UserDto,
)


def person(user: User) -> Person:
    return Person(id=user.id, name=user.name)


def user_dto(user: User) -> UserDto:
    return UserDto.model_validate(
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role_code,
            "is_active": user.is_active,
            "created_at": user.created_at,
        }
    )


async def projects_dto(session: AsyncSession, projects: Sequence[Project]) -> list[ProjectDto]:
    if not projects:
        return []
    ids = [project.id for project in projects]
    member_counts = {
        project_id: count
        for project_id, count in (
            await session.execute(
                select(ProjectMember.project_id, func.count())
                .where(ProjectMember.project_id.in_(ids))
                .group_by(ProjectMember.project_id)
            )
        ).all()
    }
    board_counts = {
        project_id: count
        for project_id, count in (
            await session.execute(
                select(Board.project_id, func.count())
                .where(Board.project_id.in_(ids))
                .group_by(Board.project_id)
            )
        ).all()
    }
    return [
        ProjectDto(
            id=project.id,
            key=project.key,
            name=project.name,
            description=project.description,
            owner_id=project.owner_id,
            timezone=project.timezone,
            member_count=member_counts.get(project.id, 0),
            board_count=board_counts.get(project.id, 0),
            created_at=project.created_at,
            updated_at=project.updated_at,
        )
        for project in projects
    ]


async def project_dto(session: AsyncSession, project: Project) -> ProjectDto:
    return (await projects_dto(session, [project]))[0]


async def members_dto(
    session: AsyncSession,
    members: Sequence[ProjectMember],
    project: Project,
) -> list[MemberDto]:
    if not members:
        return []
    users = {
        user.id: user
        for user in (
            await session.scalars(
                select(User).where(User.id.in_([member.user_id for member in members]))
            )
        ).all()
    }
    return [
        MemberDto(
            user_id=member.user_id,
            name=users[member.user_id].name,
            email=users[member.user_id].email,
            is_active=users[member.user_id].is_active,
            is_owner=member.user_id == project.owner_id,
            joined_at=member.joined_at,
        )
        for member in members
    ]


async def member_dto(session: AsyncSession, member: ProjectMember, project: Project) -> MemberDto:
    return (await members_dto(session, [member], project))[0]


def board_dto(board: Board) -> BoardDto:
    return BoardDto.model_validate(board)


def column_dto(column: Column) -> ColumnDto:
    return ColumnDto.model_validate(column)


def tag_dto(tag: Tag) -> TagDto:
    return TagDto.model_validate(tag)


async def tasks_dto(session: AsyncSession, tasks: Sequence[Task]) -> list[TaskDto]:
    if not tasks:
        return []
    task_ids = [task.id for task in tasks]
    project_ids = {task.project_id for task in tasks}
    user_ids = {task.author_id for task in tasks} | {
        task.assignee_id for task in tasks if task.assignee_id is not None
    }
    users = {
        user.id: user
        for user in (await session.scalars(select(User).where(User.id.in_(user_ids)))).all()
    }
    projects = {
        project.id: project
        for project in (
            await session.scalars(select(Project).where(Project.id.in_(project_ids)))
        ).all()
    }
    columns = {
        column.id: column
        for column in (
            await session.scalars(
                select(Column).where(Column.id.in_({task.column_id for task in tasks}))
            )
        ).all()
    }
    memberships = set(
        (
            await session.execute(
                select(ProjectMember.project_id, ProjectMember.user_id)
                .join(User, User.id == ProjectMember.user_id)
                .where(
                    ProjectMember.project_id.in_(project_ids),
                    ProjectMember.user_id.in_(user_ids),
                    User.is_active.is_(True),
                )
            )
        ).all()
    )
    tags: dict[UUID, list[UUID]] = defaultdict(list)
    for task_id, tag_id in (
        await session.execute(
            select(TaskTag.task_id, TaskTag.tag_id).where(TaskTag.task_id.in_(task_ids))
        )
    ).all():
        tags[task_id].append(tag_id)
    return [
        TaskDto.model_validate(
            {
                "id": task.id,
                "project_id": task.project_id,
                "board_id": task.board_id,
                "number": task.number,
                "key": f"{projects[task.project_id].key}-{task.number}",
                "title": task.title,
                "description": task.description,
                "column_id": task.column_id,
                "position": task.position,
                "priority": task.priority,
                "author_id": task.author_id,
                "author": person(users[task.author_id]),
                "assignee_id": task.assignee_id,
                "assignee": person(users[task.assignee_id])
                if task.assignee_id is not None
                else None,
                "assignee_is_project_member": (task.project_id, task.assignee_id) in memberships,
                "deadline": task.deadline,
                "story_points": task.story_points,
                "tag_ids": sorted(tags[task.id], key=str),
                "version": task.version,
                "is_completed": columns[task.column_id].category == "done",
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            }
        )
        for task in tasks
    ]


async def task_dto(session: AsyncSession, task: Task) -> TaskDto:
    return (await tasks_dto(session, [task]))[0]


async def comments_dto(session: AsyncSession, comments: Sequence[Comment]) -> list[CommentDto]:
    if not comments:
        return []
    users = {
        user.id: user
        for user in (
            await session.scalars(
                select(User).where(User.id.in_({comment.author_id for comment in comments}))
            )
        ).all()
    }
    return [
        CommentDto(
            id=comment.id,
            task_id=comment.task_id,
            author_id=comment.author_id,
            author=person(users[comment.author_id]),
            text=comment.text,
            created_at=comment.created_at,
        )
        for comment in comments
    ]


async def comment_dto(session: AsyncSession, comment: Comment) -> CommentDto:
    return (await comments_dto(session, [comment]))[0]


async def audits_dto(session: AsyncSession, events: Sequence[AuditEvent]) -> list[AuditDto]:
    if not events:
        return []
    users = {
        user.id: user
        for user in (
            await session.scalars(
                select(User).where(User.id.in_({event.actor_id for event in events}))
            )
        ).all()
    }
    return [
        AuditDto.model_validate(
            {
                "id": event.id,
                "task_id": event.task_id,
                "operation_id": event.operation_id,
                "event_type": event.event_type,
                "changes": event.changes,
                "actor_id": event.actor_id,
                "actor": person(users[event.actor_id]),
                "occurred_at": event.occurred_at,
            }
        )
        for event in events
    ]


async def audit_dto(session: AsyncSession, event: AuditEvent) -> AuditDto:
    return (await audits_dto(session, [event]))[0]


serialize_project = project_dto
serialize_member = member_dto
serialize_board = board_dto
serialize_column = column_dto
serialize_task = task_dto
serialize_tag = tag_dto
serialize_comment = comment_dto
serialize_audit = audit_dto
