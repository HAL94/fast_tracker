from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends

from app.constants.roles import UserRole
from app.core.schema import AppResponse
from app.dependencies.activity import validate_activity, validate_task
from app.dependencies.auth import CurrentUser, ValidateRole
from app.dependencies.db_session import DbSession
from app.domain.activity import ActivityBase, ActivityTaskBase, ActivityTypeBase, ActivityUserBase, ActivityWithType
from app.dto.activity import CreateActivityDto, CreateActivityTaskDto, CreateUserActivityDto, CreateWorklogDto
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
async def get_all_activities(session: DbSession):
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


@activity_router.get("/by-user", response_model=AppResponse[List[ActivityWithType]])
async def get_user_activities(session: DbSession, user: CurrentUser) -> AppResponse[List[ActivityWithType]]:
    """Get all activities performed by the current employee"""
    activity_service = ActivityService(session)
    result = await activity_service.get_activities_by_user(user.id)
    return AppResponse(data=result)


@activity_router.get(
    "/{activity_id}/task",
    dependencies=[Depends(ValidateRole(UserRole.USER))],
    response_model=AppResponse[List[ActivityTaskBase]],
)
async def get_activity_tasks(
    session: DbSession, user: CurrentUser, activity_id: UUID
) -> AppResponse[List[ActivityTaskBase]]:
    """Get all tasks for a given activity for the currently logged-in employee"""
    await validate_activity(session, user, activity_id)
    activity_service = ActivityService(session)
    result = await activity_service.get_all_tasks(activity_id)
    return AppResponse(data=result)


@activity_router.post(
    "/{activity_id}/task",
    dependencies=[Depends(ValidateRole(UserRole.USER))],
)
async def add_activity_task(session: DbSession, user: CurrentUser, data: CreateActivityTaskDto, activity_id: UUID):
    """Add a task to a given activity for the currently logged-in employee"""
    data.activity_id = activity_id
    await validate_activity(session, user, activity_id)
    activity_service = ActivityService(session)
    result = await activity_service.add_activity_task(data)
    return AppResponse(data=result)


@activity_router.post("/{activity_id}/task/{task_id}/log", dependencies=[Depends(ValidateRole(UserRole.USER))])
async def add_worklog(session: DbSession, user: CurrentUser, data: CreateWorklogDto, task_id: UUID, activity_id: UUID):
    """Add a worklog to a task for an activity, core endpoint for employee tracking their hours"""
    data.activity_task_id = task_id
    await validate_task(session, user, activity_id, task_id)
    activity_service = ActivityService(session)
    result = await activity_service.add_worklog(data)
    return AppResponse(data=result)
