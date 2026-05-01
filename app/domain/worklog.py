from datetime import date as Date
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.models import Worklog


class WorklogBase(BaseDomain[Worklog]):
    model: ClassVar[Worklog] = Worklog

    id: Optional[UUID] = Field(default=None)
    date: Date
    duration: Optional[float] = None
    activity_task_id: UUID
    user_id: UUID
    tenant_id: UUID
