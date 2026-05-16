from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, UnauthorizedException
from app.domain.tenant import TenantSettings
from app.models import ActivityTask, ActivityUser, Worklog
from app.repositories.tenant_repository import TenantRepository


class JournalWorklogValidation:
    """
    A wrapper class that will perform validation related tasks
    """

    def __init__(self, session: AsyncSession):
        self.session = session

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
        tenant_repo = TenantRepository(self.session)
        tenant_config = await tenant_repo.get_config(tenant_id=tenant_id)
        tenant_settings = TenantSettings.model_validate(tenant_config.settings)
        limit_hours = tenant_settings.daily_limit_hours

        if tenant_settings.is_ramadan_mode:
            limit_hours = tenant_settings.ramadan_limit_hours

        stmt = (
            select(Worklog.date, func.sum(Worklog.duration))
            .where(Worklog.user_id == user_id, Worklog.tenant_id == tenant_id)
            .where(Worklog.date.in_(dates))
            .group_by(Worklog.date)
            .having(func.sum(Worklog.duration) > limit_hours)
        )
        result = await self.session.execute(stmt)
        errors = result.all()

        if errors:
            details = ", ".join([f"{r[0]} ({r[1]}h)" for r in errors])
            raise BadRequestException(f"Daily limit exceeded {limit_hours}: {details}")
