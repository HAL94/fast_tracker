from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends

from app.constants.roles import UserRole
from app.core.schema import AppResponse
from app.dependencies.activity import validate_activity
from app.dependencies.auth import CurrentUser, ValidateRole
from app.dependencies.db_session import DbSession
from app.domain.activity import (
    ActivityBase,
    ActivityTaskBase,
    ActivityTypeBase,
    ActivityUserBase,
    ActivityWithType,
    WorklogBase,
)
from app.dto.activity import (
    CreateActivityDto,
    CreateActivityTaskDto,
    CreateUserActivityDto,
    TaskBatchDto,
)
from app.services.activity import ActivityService

activity_router = APIRouter(prefix="/activity", tags=["Activities"])


@activity_router.get("/types", response_model=AppResponse[List[ActivityTypeBase]])
async def get_all(session: DbSession) -> AppResponse[List[ActivityTypeBase]]:
    """Get all activity types for tracking"""
    activity_service = ActivityService(session)
    result = await activity_service.get_activity_types()
    return AppResponse(data=result)


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
    """Create an activity"""
    activity_service = ActivityService(session)
    result = await activity_service.create_activity(data)
    return AppResponse(data=result)


@activity_router.post(
    "/assign",
    dependencies=[Depends(ValidateRole(UserRole.ADMIN))],
    response_model=AppResponse[ActivityUserBase],
)
async def assign_user_activity_item(session: DbSession, data: CreateUserActivityDto) -> AppResponse[ActivityUserBase]:
    """Assign a specific employee to an activity, so the employee can track their time spent on it"""
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


@activity_router.post(
    "/{activity_id}/task",
    dependencies=[Depends(ValidateRole(UserRole.USER))],
    response_model=AppResponse[ActivityTaskBase],
)
async def add_activity_task(
    session: DbSession, user: CurrentUser, data: CreateActivityTaskDto, activity_id: UUID
) -> AppResponse[ActivityTaskBase]:
    """Add a task to a given activity for the currently logged-in employee"""
    data.activity_id = activity_id
    await validate_activity(session, user, activity_id)
    activity_service = ActivityService(session)
    result = await activity_service.add_activity_task(data, user.id)
    return AppResponse(data=result)


@activity_router.post(
    "/worklog-batch",
    dependencies=[Depends(ValidateRole(UserRole.USER))],
    response_model=AppResponse[List[WorklogBase]],
)
async def worklog_batch(session: DbSession, user: CurrentUser, data: TaskBatchDto) -> AppResponse[List[WorklogBase]]:
    """Add/update/delete worklog batch for multiple activities, core endpoint for employee tracking their hours"""
    activity_service = ActivityService(session)
    worklogs = await activity_service.batch_worklog(data, user.id)
    return AppResponse(data=worklogs)
