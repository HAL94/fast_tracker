from datetime import date as Date
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.mixin import BaseModelDatabaseMixin
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.models import Worklog


class WorklogBase(BaseModelDatabaseMixin[Worklog]):
    model: ClassVar[Worklog] = Worklog

    id: Optional[UUID] = Field(default=None)
    date: Date
    duration: Optional[float] = None
    activity_task_id: UUID
    user_id: UUID

    @classmethod
    async def is_owned_by(cls, session: AsyncSession, worklog_id: UUID, user_id: UUID) -> None:
        """Check if the domain is owned by the passed user_id"""
        try:
            await cls.exists(session, worklog_id, field=cls.model.id, where_clause=[cls.model.user_id == user_id])
        except NotFoundException:
            raise UnauthorizedException(message="Not allowed to access worklog resource")
