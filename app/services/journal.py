from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.activity import ActivityBase
from app.dto.journal import GetJournalDto, JournalActivity
from app.services.base import BaseService


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_journal(self, data: GetJournalDto, user_id: UUID) -> List[JournalActivity]:
        return await ActivityBase.get_journal(self.session, user_id, data.start_date, data.end_date)
