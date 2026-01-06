from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.activity import (
    ActivityBase,
    ActivityByUser,
    ActivityTaskBase,
    ActivityTypeBase,
    ActivityUserBase,
    ActivityWithType,
    WorklogBase,
)
from app.dto.activity import CreateActivityDto, CreateActivityTaskDto, CreateUserActivityDto, CreateWorklogDto
from app.services.base import BaseService


class ActivityService(BaseService):
    """Activity orchestration class-service"""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session)
        self._activity_type = ActivityTypeBase
        self._activity = ActivityBase
        self._activity_user = ActivityUserBase
        self._activity_by_user = ActivityByUser
        self._activity_task = ActivityTaskBase
        self._worklog = WorklogBase

    def _get_model(self):
        return self._activity

    async def get_activity_types(self) -> List[ActivityTypeBase]:
        """Get all activity types"""
        return await self._activity_type.get_all(self.session)

    async def get_all_activities(self) -> List[ActivityBase]:
        return await self._activity.get_all(self.session)

    async def create_activity(self, data: CreateActivityDto) -> ActivityBase:
        """Create an activity item, ADMIN ONLY"""
        return await self._activity.create(self.session, data)

    async def assign_user_to_activity_item(self, data: CreateUserActivityDto) -> ActivityUserBase:
        """Assign the employee to a specific activity so they can track their hours on it, ADMIN ONLY"""
        return await self._activity_user.create(self.session, data)

    async def get_activities_by_user(self, user_id: UUID) -> List[ActivityWithType]:
        """Get all activity items performed by an employee"""
        model = self._activity_by_user.model
        items = await self._activity_by_user.get_all(self.session, where_clause=[model.user_id == user_id])
        activity_items = [item.activity for item in items]
        return activity_items

    async def get_all_tasks(self, activity_id: UUID) -> List[ActivityTaskBase]:
        """Get all tasks for a given activity_id"""
        model = self._activity_task.model
        return await self._activity_task.get_all(self.session, where_clause=[model.activity_id == activity_id])

    async def add_activity_task(self, data: CreateActivityTaskDto) -> ActivityTaskBase:
        """An employee will add their own task for tracking for a specific activity"""
        return await self._activity_task.create(self.session, data)

    async def add_worklog(self, data: CreateWorklogDto) -> WorklogBase:
        """An employee will record their time (hours) spent of a given task"""
        return await self._worklog.create(
            self.session,
            WorklogBase(
                date=data.date,
                duration=float(data.duration),
                activity_task_id=data.activity_task_id,
            ),
        )
