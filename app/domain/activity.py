from datetime import datetime
from typing import ClassVar, List, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import selectinload

from app.core.database.mixin import BaseModelDatabaseMixin
from app.models import Activity, ActivityTask, ActivityType, ActivityUser, Worklog


class ActivityTypeBase(BaseModelDatabaseMixin[ActivityType]):
    model: ClassVar[ActivityType] = ActivityType

    @classmethod
    def relations(cls):
        return [selectinload(cls.model.activities)]

    id: Optional[UUID] = Field(default=None)
    title: str


class ActivityBase(BaseModelDatabaseMixin[Activity]):
    model: ClassVar[Activity] = Activity

    id: Optional[UUID] = Field(default=None)
    title: str
    code: str
    expected_hours: int
    activity_type_id: UUID


class ActivityWithType(ActivityBase):
    activity_type_id: UUID = Field(exclude=True)

    activity_type: ActivityTypeBase


class ActivityUserBase(BaseModelDatabaseMixin[ActivityUser]):
    """
    A link between activity items and users.
    Many users could be doing the same project activity
    """

    model: ClassVar[ActivityUser] = ActivityUser

    id: Optional[UUID] = Field(default=None)
    user_id: UUID
    activity_id: UUID
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)


class ActivityByUser(ActivityUserBase):
    @classmethod
    def relations(cls):
        return [selectinload(cls.model.activity).selectinload(ActivityBase.model.activity_type)]

    user_id: UUID = Field(exclude=True)
    id: Optional[UUID] = Field(exclude=True)
    activity_id: UUID = Field(exclude=True)
    created_at: Optional[datetime] = Field(exclude=True)
    updated_at: Optional[datetime] = Field(exclude=True)

    activity: ActivityWithType


class ActivityTaskBase(BaseModelDatabaseMixin[ActivityTask]):
    model: ClassVar[ActivityTask] = ActivityTask

    id: Optional[UUID] = Field(default=None)
    title: str
    activity_id: UUID


class ActivityTaskWorklogs(ActivityTaskBase):
    worklogs: List["WorklogBase"]


class WorklogBase(BaseModelDatabaseMixin[Worklog]):
    model: ClassVar[Worklog] = Worklog

    id: Optional[UUID] = Field(default=None)
    date: datetime
    duration: float
    activity_task_id: UUID
