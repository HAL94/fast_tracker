from uuid import UUID

from app.core.exceptions import AppException, NotFoundException, UnauthorizedException
from app.dependencies.auth import CurrentUser
from app.dependencies.db_session import DbSession
from app.domain.activity import ActivityTaskBase, ActivityUserBase


async def validate_activity(session: DbSession, user: CurrentUser, activity_id: UUID) -> None:
    """Validate if the current employee is allowed to access the activity item"""
    try:
        if not activity_id:
            raise AppException(status_code=500, message="[ValidateActivity]: activity_id could not be verified")

        model = ActivityUserBase.model
        await ActivityUserBase.get_one(
            session, activity_id, field=model.activity_id, where_clause=[model.user_id == user.id]
        )
    except NotFoundException:
        raise UnauthorizedException
    except Exception as e:
        raise e


async def validate_task(session: DbSession, user: CurrentUser, activity_id: UUID, task_id: UUID) -> None:
    try:
        await validate_activity(session, user, activity_id)

        if not task_id:
            raise AppException(status_code=500, message="[ValidateTask]: activity_task_id could not be verified")

        model = ActivityTaskBase.model
        await ActivityTaskBase.get_one(
            session, task_id, field=model.id, where_clause=[model.activity_id == activity_id]
        )
    except NotFoundException:
        raise UnauthorizedException
    except Exception as e:
        raise e
