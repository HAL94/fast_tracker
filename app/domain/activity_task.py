from datetime import datetime
from typing import ClassVar, List, Optional
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.domain.worklog import WorklogBase
from app.models import ActivityTask


class ActivityTaskBase(BaseDomain[ActivityTask]):
    model: ClassVar[ActivityTask] = ActivityTask

    id: Optional[UUID] = Field(default=None)
    title: str
    activity_id: UUID
    user_id: UUID
    tenant_id: UUID
    updated_at: datetime = Field(default=datetime.now())


class ActivityTaskWorklogs(ActivityTaskBase):
    worklogs: List[WorklogBase]
