from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager

from app.domain.activity import ActivityByUser, WorklogBase
from app.dto.journal import GetJournalDto, JournalActivity, JournalActivityTask, UserJournalDto
from app.models import ActivityTask, Worklog
from app.services.base import BaseService


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session
        self._activity_user = ActivityByUser

    async def get_journal(self, data: GetJournalDto, user_id: UUID) -> List[WorklogBase]:
        activity_user_model = self._activity_user.model
        activities = await self._activity_user.get_all(
            self.session, where_clause=[activity_user_model.user_id == user_id]
        )
        journal_activities = [
            JournalActivity.model_validate(item.activity, from_attributes=True) for item in activities
        ]
        stmt = (
            select(ActivityTask)
            .join(ActivityTask.worklogs)
            .where(ActivityTask.user_id == user_id, Worklog.date.between(data.start_date, data.end_date))
            .order_by(ActivityTask.created_at.asc(), Worklog.date.asc())
            .options(
                contains_eager(ActivityTask.worklogs),
            )
        )

        activity_task_result = await self.session.scalars(stmt)
        activity_tasks = activity_task_result.unique().all()

        # activity_tasks = await self._activity_task.get_all(
        #     self.session,
        #     where_clause=[
        #         ActivityTask.user_id == user_id,
        #     ],
        #     options=[
        #         with_loader_criteria(Worklog, Worklog.date.between(data.start_date, data.end_date)),
        #         selectinload(ActivityTask.worklogs)
        #     ],
        # )
        journal_activity_tasks = [
            JournalActivityTask.model_validate(item, from_attributes=True) for item in activity_tasks
        ]
        return UserJournalDto(project_assignments=journal_activities, tasks=journal_activity_tasks)
