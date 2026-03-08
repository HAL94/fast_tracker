from typing import List

from fastapi import APIRouter, Depends

from app.constants.roles import UserRole
from app.core.schema import AppResponse
from app.dependencies.auth import CurrentUser, ValidateRole
from app.dependencies.db_session import DbSession
from app.domain.activity import (
    ActivityBase,
    ActivityUserBase,
    ActivityWithType,
)
from app.domain.activity_task import ActivityTaskBase
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
    "/", dependencies=[Depends(ValidateRole(UserRole.ADMIN))], response_model=AppResponse[ActivityBase]
)
async def add_activity(session: DbSession, data: CreateActivityDto) -> AppResponse[ActivityBase]:
    """Create an activity. Admin Only"""
    activity_service = ActivityService(session)
    result = await activity_service.create_activity(data)
    return AppResponse(data=result)


@activity_router.post(
    "/assign",
    dependencies=[Depends(ValidateRole(UserRole.ADMIN))],
    response_model=AppResponse[ActivityUserBase],
)
async def assign_user_activity_item(session: DbSession, data: CreateUserActivityDto) -> AppResponse[ActivityUserBase]:
    """Assign a specific employee to an activity, so the employee can track their time spent on it. Admin Only"""
    activity_service = ActivityService(session)
    result = await activity_service.assign_user_to_activity_item(data)
    return AppResponse(data=result)


@activity_router.get("/employee", response_model=AppResponse[List[ActivityWithType]])
async def get_user_activities(session: DbSession, user: CurrentUser) -> AppResponse[List[ActivityWithType]]:
    """Get all activities performed by the current employee"""
    activity_service = ActivityService(session)
    result = await activity_service.get_activities_by_user(user.id)
    return AppResponse(data=result)


@activity_router.get(
    "/task",
    dependencies=[Depends(ValidateRole(UserRole.USER))],
    response_model=AppResponse[List[ActivityTaskBase]],
)
async def get_activity_tasks(session: DbSession, user: CurrentUser) -> AppResponse[List[ActivityTaskBase]]:
    """Get all tasks for the currently logged-in employee"""
    activity_service = ActivityService(session)
    result = await activity_service.get_all_tasks(user.id)
    return AppResponse(data=result)
