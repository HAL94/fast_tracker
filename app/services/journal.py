from typing import List
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, joinedload, with_loader_criteria

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
            .where(
                and_(
                    ActivityTask.user_id == user_id,
                )
            )
            .order_by(ActivityTask.created_at.desc())
            .options(
                joinedload(Activity.activity_type),
                contains_eager(Activity.tasks).selectinload(ActivityTask.worklogs),
            )
            .options(
                with_loader_criteria(
                    Worklog, and_(Worklog.date.between(data.start_date, data.end_date), Worklog.user_id == user_id)
                )
            )
        )

        result = (await self.session.scalars(stmt)).unique().all()
        return [JournalActivity.from_activity_model(item) for item in result]
