from datetime import date as Date
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.core.database.mixin import BaseModelDatabaseMixin
from app.models import Worklog


class WorklogBase(BaseModelDatabaseMixin[Worklog]):
    model: ClassVar[Worklog] = Worklog

    id: Optional[UUID] = Field(default=None)
    date: Date
    duration: Optional[float] = None
    activity_task_id: UUID
    user_id: UUID
