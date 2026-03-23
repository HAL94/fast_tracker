import logging
from datetime import date as Date
from typing import List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria

from app.core.exceptions import BadRequestException
from app.domain.activity_task import ActivityTaskBase
from app.domain.worklog import WorklogBase
from app.dto.journal import GetJournalDto, JournalActivity, TaskBatchDto
from app.models import Activity, ActivityTask, ActivityUser, Worklog
from app.services.base import BaseService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def batch_worklog(self, data: TaskBatchDto, user_id: UUID) -> List[WorklogBase]:
        """An employee will record their time (hours) spent on given tasks"""
        to_delete: List[WorklogBase] = []

        task_deletions: List[UUID] = data.deletions
        await ActivityTaskBase.delete_many(self.session, [ActivityTask.id.in_(task_deletions)], commit=False)

        affected_dates: set[Date] = set()

        upsert_result = []
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
            index_elements = ["id"]
            if task.id is None:
                index_elements = ["title", "activity_id", "month", "year"]

            current_task = await ActivityTaskBase.upsert_one(self.session, task_data, index_elements, commit=False)

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
                    index_elements = ["id"]
                    if item.id is None:
                        index_elements = ["activity_task_id", "date", "user_id"]
                    upserted_worklog = await WorklogBase.upsert_one(
                        self.session,
                        worklog,
                        index_elements,
                        commit=False,
                    )
                    upsert_result.append(upserted_worklog)

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

        logger.info(f"upserted results: {upsert_result}")
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
