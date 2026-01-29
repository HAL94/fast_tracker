from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload

from app.dto.journal import GetJournalDto, JournalActivity
from app.models import Activity, ActivityTask, Worklog
from app.services.base import BaseService


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_journal(self, data: GetJournalDto, user_id: UUID) -> List[JournalActivity]:
        stmt = (
            select(Activity)
            .join(Activity.tasks)
            .join(ActivityTask.worklogs)
            .where(ActivityTask.user_id == user_id, Worklog.date.between(data.start_date, data.end_date))
            .order_by(ActivityTask.created_at.asc(), Worklog.date.asc())
            .distinct()
            .options(
                joinedload(Activity.activity_type),
                contains_eager(Activity.tasks).contains_eager(ActivityTask.worklogs),
            )
        )
        result = (await self.session.scalars(stmt)).unique().all()
        return [JournalActivity.model_validate(item, from_attributes=True) for item in result]
