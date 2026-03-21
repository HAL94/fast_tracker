from typing import ClassVar, List, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.mixin import BaseModelDatabaseMixin
from app.core.exceptions import NotFoundException, UnauthorizedException
from app.domain.worklog import WorklogBase
from app.models import ActivityTask


class ActivityTaskBase(BaseModelDatabaseMixin[ActivityTask]):
    model: ClassVar[ActivityTask] = ActivityTask

    id: Optional[UUID] = Field(default=None)
    title: str
    activity_id: UUID
    user_id: UUID
    month: int
    year: int

    @classmethod
    async def is_owned_by(cls, session: AsyncSession, task_id: UUID,  user_id: UUID) -> None:
        """Check if the domain is owned by the passed user_id"""
        try:
            await cls.exists(session, task_id, field=cls.model.id, where_clause=[cls.model.user_id == user_id])
        except NotFoundException:
            raise UnauthorizedException(message="Not allowed to access task resource")


class ActivityTaskWorklogs(ActivityTaskBase):
    worklogs: List[WorklogBase]
