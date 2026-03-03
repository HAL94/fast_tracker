from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import selectinload

from app.core.database.mixin import BaseModelDatabaseMixin
from app.models import ActivityType


class ActivityTypeBase(BaseModelDatabaseMixin[ActivityType]):
    model: ClassVar[ActivityType] = ActivityType

    @classmethod
    def relations(cls):
        return [selectinload(ActivityType.activities)]

    id: Optional[UUID] = Field(default=None)
    title: str
