from datetime import date as Date
from typing import List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria

from app.core.exceptions import BadRequestException, IntegrityException, NotFoundException, UnauthorizedException
from app.domain.activity_task import ActivityTaskBase
from app.domain.worklog import WorklogBase
from app.dto.activity import TaskBatchDto
from app.dto.journal import GetJournalDto, JournalActivity
from app.models import Activity, ActivityTask, ActivityUser, Worklog
from app.services.base import BaseService


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def batch_worklog(self, data: TaskBatchDto, user_id: UUID) -> List[WorklogBase]:
        """An employee will record their time (hours) spent on given tasks"""
        to_delete: List[WorklogBase] = []
        to_upsert: List[WorklogBase] = []

        task_deletions: List[UUID] = data.deletions
        await ActivityTaskBase.delete_many(self.session, [ActivityTask.id.in_(task_deletions)], commit=False)

        affected_dates: set[Date] = set()

        for task in data.tasks:
            for item in task.worklogs:
                affected_dates.add(item.date)
            if task.id:
                await ActivityTaskBase.is_owned_by(self.session, task.id, user_id)

            task_data = ActivityTaskBase(
                title=task.title,
                activity_id=task.activity_id,
                id=task.id,
                user_id=user_id,
                month=task.month,
                year=task.year,
            )
            current_task = await ActivityTaskBase.upsert_one(self.session, task_data, commit=False)

            for item in task.worklogs:
                if item.id:
                    await WorklogBase.is_owned_by(self.session, item.id, user_id)

                worklog = WorklogBase(
                    id=item.id,
                    date=item.date,
                    duration=item.duration,
                    activity_task_id=current_task.id,
                    user_id=user_id,
                )
                if worklog.id and (worklog.duration is None or worklog.duration == 0):
                    to_delete.append(worklog)
                else:
                    to_upsert.append(worklog)

        upsert_result = await WorklogBase.upsert_many(
            self.session,
            to_upsert,
            commit=False,
        )
        await WorklogBase.delete_many(self.session, [Worklog.id.in_([item.id for item in to_delete])], commit=False)

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
            raise BadRequestException(f"Daily limit exceeded: {details}")

        await self.session.commit()
        return upsert_result

    async def get_journal(self, data: GetJournalDto, user_id: UUID) -> List[JournalActivity]:
        try:
            start_month = data.start_date.month
            end_month = data.end_date.month
            start_year = data.start_date.year
            end_year = data.end_date.year
            stmt = (
                select(Activity)
                .join(Activity.user_activities)
                .where(ActivityUser.user_id == user_id)
                .options(
                    joinedload(Activity.activity_type),
                    selectinload(Activity.tasks).selectinload(ActivityTask.worklogs),
                    with_loader_criteria(
                        ActivityTask,
                        and_(
                            ActivityTask.user_id == user_id,
                            and_(
                                ActivityTask.month.between(start_month, end_month),
                                ActivityTask.year.between(start_year, end_year),
                            ),
                        ),
                    ),
                )
            )
            result = (await self.session.scalars(stmt)).all()
            return [JournalActivity.from_activity_model(item) for item in result]
        except Exception as e:
            raise e
