from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.core.database.mixin import BaseModelDatabaseMixin
from app.domain.activity_type import ActivityTypeBase
from app.models import Activity, ActivityUser


class ActivityBase(BaseModelDatabaseMixin[Activity]):
    model: ClassVar[Activity] = Activity

    id: Optional[UUID] = Field(default=None)
    title: str
    code: str
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
    assigned_by_id: Optional[UUID] = Field(default=None)
