from typing import Any, Optional
from uuid import UUID

from sqlalchemy import insert, select

from app.domain.activity import ActivityBase, ActivityUserBase, ActivityWithType
from app.domain.activity_type import ActivityTypeBase
from app.domain.base import BaseDomain
from app.domain.user import UserWithActivities
from app.dto.activity import CreateUserActivityWithTenantDto
from app.models import Activity, ActivityType, ActivityUser, User
from app.repositories.base_repository import BaseRepository


class ActivityRepository(BaseRepository[ActivityBase, Activity]):
    __model__ = Activity

    def domain_model(self, data: dict[str, Any], as_domain: Optional[BaseDomain] = None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return ActivityBase.model_validate(data, from_attributes=True)

    async def get_activity_types(self) -> list[ActivityTypeBase]:
        """
        Fetch activity types

        Returns:
            list of activity types
        """
        stmt = select(ActivityType).options(*ActivityTypeBase.relations())
        result = await self.session.scalars(stmt)

        return [ActivityTypeBase.model_validate(obj, from_attributes=True) for obj in result]

    async def assign_employee(self, data: CreateUserActivityWithTenantDto) -> ActivityUserBase:
        """
        Assign an employee to a particular activity for a given tenant

        Arguments:
            data: object to insert

        Returns:
            obj: created result
        """
        stmt = insert(ActivityUser).values(data.model_dump(by_alias=False)).returning(ActivityUser)

        result = (await self.session.execute(stmt)).scalar_one()

        await self.session.commit()

        return ActivityUserBase.model_validate(result, from_attributes=True)

    async def get_user_activities(self, user_id: UUID) -> list[ActivityWithType]:
        """
        Return the activities undertaken by a given user

        Arguments:
            user_id: UUID of user

        Returns:
            activity_items: list of activities and their types
        """
        stmt = select(User).where(User.id == user_id).options(*UserWithActivities.relations())

        current_user = await self.session.scalar(stmt)
        activity_items = [
            ActivityWithType.model_validate(item, from_attributes=True) for item in current_user.activity_items
        ]
        return activity_items
