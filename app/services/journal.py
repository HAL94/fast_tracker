import logging
from datetime import date as Date
from typing import Any, List
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria

from app.core.exceptions import BadRequestException, UnauthorizedException
from app.domain.activity import ActivityUserBase
from app.domain.activity_task import ActivityTaskBase
from app.domain.worklog import WorklogBase
from app.dto.journal import GetJournalDto, JournalActivity, TaskBatchDto
from app.models import Activity, ActivityTask, ActivityUser, Worklog
from app.services.base import BaseService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _validate_activities(self, activities: set[UUID], user_id: UUID) -> None:
        stmt = select(ActivityUser.activity_id).where(
            ActivityUser.user_id == user_id, ActivityUser.activity_id.in_(activities)
        )

        result = (await self.session.execute(stmt)).scalars().all()
        result_set = set(result)

        if activities - result_set:
            raise UnauthorizedException(message="Not allowed to access activity resource")

    async def _validate_tasks(self, tasks: set[UUID], user_id: UUID) -> dict[str, Any]:
        stmt = select(ActivityTask.id, ActivityTask.activity_id).where(
            ActivityTask.user_id == user_id, ActivityTask.id.in_(tasks)
        )

        result = (await self.session.execute(stmt)).all()

        task_activity_map: dict[UUID, UUID] = {row[0]: row[1] for row in result}

        if tasks - set(task_activity_map.keys()):
            raise UnauthorizedException("Not allowed to access task resource")

        return task_activity_map

    async def _validate_worklogs(self, worklogs: set[UUID], user_id: UUID) -> None:
        stmt = select(Worklog.id).where(Worklog.user_id == user_id, Worklog.id.in_(worklogs))

        result_set = set((await self.session.execute(stmt)).scalars().all())

        if worklogs - result_set:
            raise UnauthorizedException("Not allowed to access worklog resource")

    async def batch_worklog(self, data: TaskBatchDto, user_id: UUID) -> List[WorklogBase]:
        """An employee will record their time (hours) spent on given tasks"""

        task_deletions: List[UUID] = data.deletions

        # Process tasks not marked for deletion
        filtered_tasks = [task for task in data.tasks if task.id not in task_deletions]

        # Deletion takes precedence over updates
        await ActivityTaskBase.delete_many(self.session, [ActivityTask.id.in_(task_deletions)], commit=False)

        # Worklogs to delete and update
        to_delete: List[WorklogBase] = []
        to_upsert: List[WorklogBase] = []
        affected_dates: set[Date] = set()

        activity_ids: set[UUID] = {task.activity_id for task in filtered_tasks}
        task_ids: set[UUID] = {task.id for task in filtered_tasks if task.id}
        worklogs_ids: set[UUID] = {worklog.id for task in filtered_tasks for worklog in task.worklogs if worklog.id}

        await self._validate_activities(activity_ids, user_id)
        task_activity_map = await self._validate_tasks(task_ids, user_id)
        await self._validate_worklogs(worklogs_ids, user_id)

        upsert_result = []
        for task in filtered_tasks:
            if task.id:
                existing_activity_id = task_activity_map.get(task.id)

                if existing_activity_id and existing_activity_id != task.activity_id:
                    raise BadRequestException(
                        f"Task '{task.title}' is already linked to a different activity. "
                        "Moving tasks is not allowed; please create a new task under target activity."
                    )
            task_data = ActivityTaskBase(
                title=task.title,
                activity_id=task.activity_id,
                id=task.id,
                user_id=user_id,
                month=task.month,
                year=task.year,
            )
            index_elements = ["id"]
            if not task.id:
                index_elements = ["title", "activity_id", "month", "year"]

            current_task = await ActivityTaskBase.upsert_one(self.session, task_data, index_elements, commit=False)

            for item in task.worklogs:
                affected_dates.add(item.date)
                worklog_data = WorklogBase(
                    id=item.id,
                    date=item.date,
                    duration=item.duration,
                    activity_task_id=current_task.id,
                    user_id=user_id,
                )
                if worklog_data.id and (worklog_data.duration is None or worklog_data.duration == 0):
                    to_delete.append(worklog_data)
                else:
                    to_upsert.append(worklog_data)

        await WorklogBase.delete_many(self.session, [Worklog.id.in_([item.id for item in to_delete])], commit=False)
        upsert_result = await WorklogBase.upsert_many(
            self.session, to_upsert, ["activity_task_id", "date", "user_id"], commit=False
        )

        await self.session.flush()

        logger.info(f"Dates to check against: {affected_dates}")

        stmt = (
            select(Worklog.date, func.sum(Worklog.duration))
            .where(Worklog.user_id == user_id)
            .where(Worklog.date.in_(affected_dates))
            .group_by(Worklog.date)
            .having(func.sum(Worklog.duration) > 8)
        )
        result = await self.session.execute(stmt)
        errors = result.all()

        if errors:
            details = ", ".join([f"{r[0]} ({r[1]}h)" for r in errors])
            raise BadRequestException(f"Daily limit exceeded: {details}")

        await self.session.commit()

        logger.info(f"Worklog processing done: Upserted {len(upsert_result)} records.")
        return upsert_result

    async def get_journal(self, data: GetJournalDto, user_id: UUID) -> List[JournalActivity]:
        try:
            start_month = data.start_date.month
            end_month = data.end_date.month
            start_year = data.start_date.year
            end_year = data.end_date.year
            stmt = (
                select(Activity)
                .join(Activity.user_activities)
                .where(ActivityUser.user_id == user_id)
                .options(
                    joinedload(Activity.activity_type),
                    selectinload(Activity.tasks).selectinload(ActivityTask.worklogs),
                    with_loader_criteria(
                        ActivityTask,
                        and_(
                            ActivityTask.user_id == user_id,
                            and_(
                                ActivityTask.month.between(start_month, end_month),
                                ActivityTask.year.between(start_year, end_year),
                            ),
                        ),
                    ),
                )
            )
            result = (await self.session.scalars(stmt)).all()
            return [JournalActivity.from_activity_model(item) for item in result]
        except Exception as e:
            raise e
