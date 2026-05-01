from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria

from app.core.exceptions import BadRequestException, UnauthorizedException
from app.dto.journal import GetJournalDto, JournalActivity
from app.models import Activity, ActivityTask, ActivityUser, Worklog
from app.repositories.task_repository import ActivityTaskRepository
from app.repositories.worklog_repository import WorklogRepository


class JournalRepository:
    """
    Repository for journal-related data access operations.
    Handles validation, aggregation, and retrieval of journal data.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._task_repo = ActivityTaskRepository(session=session)
        self._worklog_repo = WorklogRepository(session=session)

    async def validate_activities(self, activities: set[UUID], user_id: UUID, tenant_id: UUID) -> None:
        """
        Validate that a user has access to the given activities.

        Arguments:
            `activities`: set of activity IDs to validate
            `user_id`: the user ID
            `tenant_id`: the tenant ID

        Raises:
            UnauthorizedException if user doesn't have access to any of the activities
        """
        stmt = select(ActivityUser.activity_id).where(
            ActivityUser.user_id == user_id,
            ActivityUser.tenant_id == tenant_id,
            ActivityUser.activity_id.in_(activities),
        )

        result = (await self.session.execute(stmt)).scalars().all()
        result_set = set(result)

        if activities - result_set:
            raise UnauthorizedException(message="Not allowed to access activity resource")

    async def validate_tasks(self, tasks: set[UUID], user_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """
        Validate that a user has access to the given tasks and return task-to-activity mapping.

        Arguments:
            `tasks`: set of task IDs to validate
            `user_id`: the user ID
            `tenant_id`: the tenant ID

        Returns:
            dict mapping task IDs to activity IDs

        Raises:
            UnauthorizedException if user doesn't have access to any of the tasks
        """
        stmt = select(ActivityTask.id, ActivityTask.activity_id).where(
            ActivityTask.user_id == user_id, ActivityTask.tenant_id == tenant_id, ActivityTask.id.in_(tasks)
        )

        result = (await self.session.execute(stmt)).all()

        task_activity_map: dict[UUID, UUID] = {row[0]: row[1] for row in result}

        if tasks - set(task_activity_map.keys()):
            raise UnauthorizedException("Not allowed to access task resource")

        return task_activity_map

    async def validate_worklogs(self, worklogs: set[UUID], user_id: UUID, tenant_id: UUID) -> None:
        """
        Validate that a user has access to the given worklogs.

        Arguments:
            `worklogs`: set of worklog IDs to validate
            `user_id`: the user ID
            `tenant_id`: the tenant ID

        Raises:
            UnauthorizedException if user doesn't have access to any of the worklogs
        """
        stmt = select(Worklog.id).where(
            Worklog.user_id == user_id, Worklog.tenant_id == tenant_id, Worklog.id.in_(worklogs)
        )

        result_set = set((await self.session.execute(stmt)).scalars().all())

        if worklogs - result_set:
            raise UnauthorizedException("Not allowed to access worklog resource")

    async def cleanup_empty_tasks(self, user_id: UUID, tenant_id: UUID) -> None:
        """
        Find and delete any activity tasks for a given user that do not have any worklogs.

        Arguments:
            `user_id`: the user ID
            `tenant_id`: the tenant ID
        """
        subq = not_(exists().where(Worklog.activity_task_id == ActivityTask.id))

        stmt = (
            delete(ActivityTask).where(ActivityTask.user_id == user_id, ActivityTask.tenant_id == tenant_id).where(subq)
        )

        await self.session.execute(stmt)

    async def validate_daily_worklog_hours(self, user_id: UUID, dates: set[datetime], tenant_id: UUID) -> None:
        """
        Validate that worklogs for the given user and dates do not exceed 8 hours per day.

        Arguments:
            `user_id`: the user ID
            `dates`: set of dates to validate
            `tenant_id`: the tenant ID

        Raises:
            BadRequestException if daily limit is exceeded on any date
        """
        stmt = (
            select(Worklog.date, func.sum(Worklog.duration))
            .where(Worklog.user_id == user_id, Worklog.tenant_id == tenant_id)
            .where(Worklog.date.in_(dates))
            .group_by(Worklog.date)
            .having(func.sum(Worklog.duration) > 8)
        )
        result = await self.session.execute(stmt)
        errors = result.all()

        if errors:
            details = ", ".join([f"{r[0]} ({r[1]}h)" for r in errors])
            raise BadRequestException(f"Daily limit exceeded: {details}")

    async def get_journal(self, data: GetJournalDto, user_id: UUID, tenant_id: UUID) -> list[JournalActivity]:
        """
        Retrieve journal activities for a user within a date range.

        Arguments:
            `data`: GetJournalDto with start_date and end_date
            `user_id`: the user ID
            `tenant_id`: the tenant ID

        Returns:
            list of JournalActivity objects
        """
        try:
            stmt = (
                select(Activity)
                .join(Activity.user_activities)
                .where(
                    Activity.tenant_id == tenant_id,
                    ActivityUser.user_id == user_id,
                    ActivityUser.tenant_id == tenant_id,
                )
                .options(
                    joinedload(Activity.activity_type),
                    selectinload(Activity.tasks).selectinload(ActivityTask.worklogs),
                    with_loader_criteria(
                        ActivityTask,
                        and_(
                            ActivityTask.user_id == user_id,
                            ActivityTask.tenant_id == tenant_id,
                            ActivityTask.worklogs.any(Worklog.date.between(data.start_date, data.end_date)),
                        ),
                    ),
                    with_loader_criteria(
                        Worklog,
                        and_(
                            Worklog.user_id == user_id,
                            Worklog.tenant_id == tenant_id,
                            Worklog.date.between(data.start_date, data.end_date),
                        ),
                    ),
                )
            )
            result = (await self.session.scalars(stmt)).all()
            return [JournalActivity.from_activity_model(item) for item in result]
        except Exception as e:
            raise e

    def get_task_repository(self) -> ActivityTaskRepository:
        """Get the task repository for task-specific operations."""
        return self._task_repo

    def get_worklog_repository(self) -> WorklogRepository:
        """Get the worklog repository for worklog-specific operations."""
        return self._worklog_repo
