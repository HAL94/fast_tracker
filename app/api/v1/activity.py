from typing import List

from fastapi import APIRouter, Depends

from app.constants.roles import UserRole
from app.core.exceptions import BadRequestException, IntegrityException
from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser, TenantId, ValidateRole
from app.dependencies.db_session import DbSession
from app.domain.activity import (
    ActivityBase,
    ActivityUserBase,
)
from app.dto.activity import (
    CreateActivityDto,
    CreateActivityWithTenantDto,
    CreateUserActivityDto,
    CreateUserActivityWithTenantDto,
)
from app.services.activity import ActivityService

activity_router = APIRouter(prefix="/activity", tags=["Activities"])


@activity_router.get(
    "/", dependencies=[Depends(ValidateRole(UserRole.ADMIN))], response_model=AppResponse[List[ActivityBase]]
)
async def get_all_activities(session: DbSession, tenant_id: TenantId) -> AppResponse[List[ActivityBase]]:
    """Get all created activities. Admin Only"""
    activity_service = ActivityService(session)
    result = await activity_service.get_all_activities(tenant_id=tenant_id)
    return AppResponse(data=result)


@activity_router.post(
    "/", dependencies=[Depends(ValidateRole(UserRole.ADMIN))], response_model=AppResponse[ActivityBase], status_code=201
)
async def add_activity(session: DbSession, data: CreateActivityDto, tenant_id: TenantId) -> AppResponse[ActivityBase]:
    """Create an activity"""
    try:
        activity_service = ActivityService(session)
        result = await activity_service.create_activity(
            CreateActivityWithTenantDto(
                activity_type_id=data.activity_type_id, title=data.title, code=data.code, tenant_id=tenant_id
            ),
        )
        return AppResponse(data=result, status_code=201)
    except IntegrityException:
        # Do not reveal integrity error
        raise BadRequestException("400 Bad Request")


@activity_router.post(
    "/assign",
    dependencies=[Depends(ValidateRole(UserRole.ADMIN))],
    response_model=AppResponse[ActivityUserBase],
    status_code=201,
)
async def assign_user_activity_item(
    session: DbSession, data: CreateUserActivityDto, user: CurrentUser
) -> AppResponse[ActivityUserBase]:
    """Assign a specific employee to an activity, so the employee can track their time spent on it"""
    try:
        activity_service = ActivityService(session)
        result = await activity_service.assign_user_to_activity_item(
            CreateUserActivityWithTenantDto(
                user_id=data.user_id, activity_id=data.activity_id, tenant_id=user.tenant_id, assigned_by_id=user.id
            )
        )
        return AppResponse(data=result)
    except IntegrityException:
        raise BadRequestException("400 Bad Request")
