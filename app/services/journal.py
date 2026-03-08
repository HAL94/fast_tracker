from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.domain.activity import ActivityBase
from app.domain.activity_task import ActivityTaskBase
from app.domain.reporting_period import ReportingPeriodBase
from app.domain.worklog import WorklogBase
from app.dto.journal import GetJournalDto, JournalActivity, ReportingPeriodQueryDto, TaskBatchDto
from app.models import Worklog
from app.services.base import BaseService
from app.utils.date_utils import get_last_day_of_month


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_journal(self, data: GetJournalDto, user_id: UUID) -> List[JournalActivity]:
        return await ActivityBase.get_journal(self.session, user_id, data.period_id)

    async def get_or_create_period(self, data: ReportingPeriodQueryDto) -> ReportingPeriodBase:
        """Get or create the period"""
        ReportingPeriod = ReportingPeriodBase.model
        start_date = datetime(data.year, data.month, 1)
        end_date = datetime(data.year, data.month, get_last_day_of_month(data.month, data.year))
        existing_period = await ReportingPeriodBase.get_one(
            self.session,
            where_clause=[
                and_(
                    ReportingPeriod.start_date == start_date,
                    ReportingPeriod.end_date == end_date,
                )
            ],
            raise_not_found=False,
        )
        if not existing_period:
            return await ReportingPeriodBase.create(
                self.session, ReportingPeriodBase(start_date=start_date, end_date=end_date)
            )
        return existing_period

    async def batch_worklog(self, data: TaskBatchDto, user_id: UUID) -> List[WorklogBase]:
        """An employee will record their time (hours) spent on given tasks"""
        to_delete: List[WorklogBase] = []
        upserted_logs: List[WorklogBase] = []
        to_upsert: List[WorklogBase] = []
        task_deletions: List[UUID] = data.deletions
        await self._activity_task.delete_many(
            self.session, [ActivityTaskBase.model.id.in_(task_deletions)], commit=False
        )
        for task in data.tasks:
            affected_dates = {item.date for item in task.worklogs}

            task_data = ActivityTaskBase(title=task.title, activity_id=task.activity_id, id=task.id, user_id=user_id)
            current_task = await self._activity_task.upsert_one(self.session, task_data, commit=False)

            for item in task.worklogs:
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

        upsert_result = await self._worklog.upsert_many(
            self.session,
            to_upsert,
            commit=False,
        )
        upserted_logs.extend(upsert_result)
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
            raise BadRequestException(f"Daily limit exceeded: {details}")

        await self.session.commit()
        return upsert_result
