from typing import ClassVar, List, Optional
from uuid import UUID

from pydantic import Field

from app.core.database.mixin import BaseModelDatabaseMixin
from app.domain.worklog import WorklogBase
from app.models import ActivityTask


class ActivityTaskBase(BaseModelDatabaseMixin[ActivityTask]):
    model: ClassVar[ActivityTask] = ActivityTask

    id: Optional[UUID] = Field(default=None)
    period_id: UUID
    title: str
    activity_id: UUID
    user_id: UUID


class ActivityTaskWorklogs(ActivityTaskBase):
    worklogs: List[WorklogBase]
