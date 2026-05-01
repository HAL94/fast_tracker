import logging
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException
from app.domain.activity import (
    ActivityBase,
    ActivityTypeBase,
    ActivityUserBase,
    ActivityWithType,
)
from app.domain.activity_task import ActivityTaskBase
from app.dto.activity import (
    CreateActivityWithTenantDto,
    CreateUserActivityWithTenantDto,
)
from app.models import User
from app.repositories.activity_repository import ActivityRepository
from app.repositories.task_repository import ActivityTaskRepository
from app.repositories.user_repository import UserRepository
from app.services.base import BaseService

logger = logging.getLogger("uvicorn.info")
logger.setLevel(logging.INFO)


class ActivityService(BaseService):
    """Activity orchestration class-service"""

    def __init__(self, session: AsyncSession):
        super().__init__(session=session)
        self._activity_repo = ActivityRepository(session)
        self._task_repo = ActivityTaskRepository(session)
        self._user = UserRepository(session)

    async def get_activity_types(self) -> List[ActivityTypeBase]:
        """Get all activity types"""
        return await self._activity_repo.get_activity_types()

    async def get_all_activities(self, tenant_id: UUID) -> List[ActivityBase]:
        return await self._activity_repo.get_many(where_clause=[ActivityBase.model.tenant_id == tenant_id])

    async def create_activity(self, data: CreateActivityWithTenantDto) -> ActivityBase:
        """Create an activity item, ADMIN ONLY"""
        return await self._activity_repo.create_one(data, commit=True)

    async def assign_user_to_activity_item(
        self, data: CreateUserActivityWithTenantDto, tenant_id: UUID
    ) -> ActivityUserBase:
        """Assign the employee to a specific activity so they can track their hours on it, ADMIN ONLY"""
        found_user = await self._user.get_one([User.id == data.user_id])
        if found_user.tenant_id != tenant_id:
            # Obfuscate the actual reason the request is rejected
            raise BadRequestException("Invalid request")
        return await self._activity_repo.assign_employee(data)

    async def get_activities_by_user(self, user_id: UUID) -> List[ActivityWithType]:
        """Get all activity items performed by an employee"""
        return await self._activity_repo.get_user_activities(user_id)

    async def get_all_tasks(self, user_id: UUID) -> List[ActivityTaskBase]:
        """Get all tasks for a given user_id"""
        model = ActivityTaskBase.model
        return await self._task_repo.get_many(where_clause=[model.user_id == user_id])
