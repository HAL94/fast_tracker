from typing import List
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
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
from app.dto.activity import (
    CreateActivityDto,
    CreateActivityTaskDto,
    CreateUserActivityDto,
    WorklogBatchDto,
)
from app.models import Worklog
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

    async def get_all_tasks(self, user_id: UUID) -> List[ActivityTaskBase]:
        """Get all tasks for a given user_id"""
        model = self._activity_task.model
        return await self._activity_task.get_all(self.session, where_clause=[model.user_id == user_id])

    async def add_activity_task(self, data: CreateActivityTaskDto) -> ActivityTaskBase:
        """An employee will add their own task for tracking for a specific activity"""
        return await self._activity_task.create(self.session, data)

    async def batch_worklog(self, data: WorklogBatchDto, user_id: UUID) -> List[WorklogBase]:
        """An employee will record their time (hours) spent on given tasks"""
        affected_dates = {item.date for item in data.worklogs}
        to_delete: List[WorklogBase] = []
        to_upsert: List[WorklogBase] = []

        created_logs: List[WorklogBase] = []

        for item in data.worklogs:
            worklog = WorklogBase(
                id=item.id, date=item.date, duration=item.duration, activity_task_id=item.task_id, user_id=user_id
            )
            if worklog.id and (worklog.duration is None or worklog.duration == 0):
                to_delete.append(worklog)
            else:
                to_upsert.append(worklog)

        upsert_result = await self._worklog.upsert_many(
            self.session,
            to_upsert,
            commit=False,
        )
        created_logs.extend(upsert_result)

        await self._worklog.delete_many(self.session, [Worklog.id.in_([item.id for item in to_delete])], commit=False)

        await self.session.flush()

        stmt = (
            select(Worklog.date, func.sum(Worklog.duration))
            .where(Worklog.user_id == user_id)
            .where(Worklog.date.in_(affected_dates))
            .group_by(Worklog.date)
            .having(func.sum(Worklog.duration) > 8)
        )
        result = await self.session.execute(stmt)
        errors = result.all()

        if errors:
            details = ", ".join([f"{r[0]} ({r[1]}h)" for r in errors])
            raise HTTPException(status_code=400, detail=f"Daily limit exceeded: {details}")

        await self.session.commit()
        return created_logs
