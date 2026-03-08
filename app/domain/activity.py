from datetime import datetime
from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria

from app.core.database.mixin import BaseModelDatabaseMixin
from app.domain.activity_type import ActivityTypeBase
from app.domain.reporting_period import ReportingPeriodBase
from app.dto.journal import JournalActivity
from app.models import Activity, ActivityTask, ActivityUser, Worklog


class ActivityBase(BaseModelDatabaseMixin[Activity]):
    model: ClassVar[Activity] = Activity

    id: Optional[UUID] = Field(default=None)
    title: str
    code: str
    activity_type_id: UUID

    @classmethod
    async def get_journal(cls, session: AsyncSession, user_id: UUID, period_id: UUID):
        try:
            reporting_period = await ReportingPeriodBase.get_one(session, period_id)
            stmt = (
                select(Activity)
                .join(Activity.user_activities)
                .where(ActivityUser.user_id == user_id)
                .options(
                    joinedload(Activity.activity_type),
                    selectinload(Activity.tasks).selectinload(ActivityTask.worklogs),
                    with_loader_criteria(
                        ActivityTask,
                        and_(ActivityTask.user_id == user_id, ActivityTask.period_id == reporting_period.id),
                    ),
                    with_loader_criteria(
                        Worklog,
                        and_(
                            Worklog.date.between(reporting_period.start_date, reporting_period.end_date),
                            Worklog.user_id == user_id,
                        ),
                    ),
                )
                .order_by(Activity.created_at.desc())
            )
            result = (await session.scalars(stmt)).all()
            return [JournalActivity.from_activity_model(item) for item in result]
        except Exception as e:
            raise e


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
