from typing import List

from fastapi import APIRouter, Depends

from app.constants.roles import UserRole
from app.core.exceptions import BadRequestException, IntegrityException
from app.core.schema import AppResponse
from app.dependencies.auth import ValidateRole
from app.dependencies.db_session import DbSession
from app.domain.activity import (
    ActivityBase,
    ActivityUserBase,
)
from app.dto.activity import (
    CreateActivityDto,
    CreateUserActivityDto,
)
from app.services.activity import ActivityService

activity_router = APIRouter(prefix="/activity", tags=["Activities"])


@activity_router.get(
    "/", dependencies=[Depends(ValidateRole(UserRole.ADMIN))], response_model=AppResponse[List[ActivityBase]]
)
async def get_all_activities(session: DbSession) -> AppResponse[List[ActivityBase]]:
    """Get all created activities. Admin Only"""
    activity_service = ActivityService(session)
    result = await activity_service.get_all_activities()
    return AppResponse(data=result)


@activity_router.post(
    "/", dependencies=[Depends(ValidateRole(UserRole.ADMIN))], response_model=AppResponse[ActivityBase], status_code=201
)
async def add_activity(session: DbSession, data: CreateActivityDto) -> AppResponse[ActivityBase]:
    """Create an activity"""
    try:
        activity_service = ActivityService(session)
        result = await activity_service.create_activity(data)
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
async def assign_user_activity_item(session: DbSession, data: CreateUserActivityDto) -> AppResponse[ActivityUserBase]:
    """Assign a specific employee to an activity, so the employee can track their time spent on it"""
    try:
        activity_service = ActivityService(session)
        result = await activity_service.assign_user_to_activity_item(data)
        return AppResponse(data=result)
    except IntegrityException:
        raise BadRequestException("400 Bad Request")
