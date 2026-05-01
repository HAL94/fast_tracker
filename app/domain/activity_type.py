from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import selectinload

from app.domain.base import BaseDomain
from app.models import ActivityType


class ActivityTypeBase(BaseDomain[ActivityType]):
    model: ClassVar[ActivityType] = ActivityType

    @classmethod
    def relations(cls):
        return [selectinload(ActivityType.activities)]

    id: Optional[UUID] = Field(default=None)
    title: str
