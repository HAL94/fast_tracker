from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import selectinload

from app.core.database.mixin import BaseModelDatabaseMixin
from app.domain.activity_task import ActivityTaskBase
from app.models import ReportingPeriod


class ReportingPeriodBase(BaseModelDatabaseMixin):
    model: ClassVar[ReportingPeriod] = ReportingPeriod

    id: Optional[UUID] = Field(default=None)
    start_date: datetime
    end_date: datetime
    is_blocked: bool = Field(default=False)

    @classmethod
    def get_or_create_period(cls):
        pass


class ReportingPeriodTasks(ReportingPeriodBase):
    @classmethod
    def relations(cls):
        return [selectinload(ReportingPeriod.tasks)]

    tasks: Optional[list[ActivityTaskBase]] = Field(default=[])
