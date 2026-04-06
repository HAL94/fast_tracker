import logging
from datetime import date as Date
from datetime import datetime
from typing import Any, List
from uuid import UUID

from sqlalchemy import and_, delete, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria

from app.core.exceptions import BadRequestException, UnauthorizedException
from app.domain.activity_task import ActivityTaskBase
from app.domain.worklog import WorklogBase
from app.dto.journal import GetJournalDto, JournalActivity, TaskBatchDto
from app.models import Activity, ActivityTask, ActivityUser, Worklog
from app.services.base import BaseService

logger = logging.getLogger("uvicorn")
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

        logger.info(f"tasks: {tasks}, task_map: {task_activity_map}")

        if tasks - set(task_activity_map.keys()):
            raise UnauthorizedException("Not allowed to access task resource")

        return task_activity_map

    async def _validate_worklogs(self, worklogs: set[UUID], user_id: UUID) -> None:
        stmt = select(Worklog.id).where(Worklog.user_id == user_id, Worklog.id.in_(worklogs))

        result_set = set((await self.session.execute(stmt)).scalars().all())

        if worklogs - result_set:
            raise UnauthorizedException("Not allowed to access worklog resource")

    async def _cleanup_empty_tasks(self, user_id: UUID) -> None:
        """Find any activity tasks for a given user that do not have any worklogs and delete them"""

        subq = exists().where(Worklog.activity_task_id == ActivityTask.id)

        stmt = delete(ActivityTask).where(ActivityTask.user_id == user_id).where(~subq)

        await self.session.execute(stmt)

    async def _validate_worklogs_8_hours(self, user_id: UUID, dates: set[datetime]) -> None:
        """Validate if the worklogs for the given user, do not exceed 8 hours when grouped by day"""
        stmt = (
            select(Worklog.date, func.sum(Worklog.duration))
            .where(Worklog.user_id == user_id)
            .where(Worklog.date.in_(dates))
            .group_by(Worklog.date)
            .having(func.sum(Worklog.duration) > 8)
        )
        result = await self.session.execute(stmt)
        errors = result.all()

        if errors:
            details = ", ".join([f"{r[0]} ({r[1]}h)" for r in errors])
            raise BadRequestException(f"Daily limit exceeded: {details}")

    async def _process_worklogs(self, user_id: UUID, data: TaskBatchDto) -> None:
        """Go through each task and attempt to update/add/delete to reflect the grid status"""
        tasks = data.tasks
        # Worklogs to deleted
        to_delete: List[WorklogBase] = []
        # Worklogs to be updated/created
        to_upsert: List[WorklogBase] = []

        # unique set of dates belonging to all worklogs
        affected_dates: set[Date] = set()
        # Result of created and updated worklogs
        upsert_result = []

        for task in tasks:
            task_data = ActivityTaskBase(
                title=task.title, activity_id=task.activity_id, user_id=user_id, updated_at=datetime.now()
            )

            index_elements = ["title", "activity_id", "user_id"]
            field_value = task.title
            target_field = ActivityTask.title
            where_clause = [ActivityTask.user_id == user_id]

            if task.id:
                field_value = task.id
                target_field = ActivityTask.id
            else:
                where_clause.extend([ActivityTask.activity_id == task.activity_id])

            task_found = await ActivityTaskBase.get_one(
                self.session,
                field_value,
                field=target_field,
                where_clause=where_clause,
                raise_not_found=False,
            )
            is_new_task = task_found is None
            current_task = await ActivityTaskBase.upsert_one(self.session, task_data, index_elements, commit=False)

            if is_new_task or task_found.id != current_task.id:
                worklog_ids = [worklog.id for worklog in task.worklogs if worklog.id]

                if len(worklog_ids) > 0:
                    # MOVE the logs to new task
                    await self.session.execute(
                        update(Worklog)
                        .where(Worklog.id.in_(worklog_ids))
                        .values(activity_task_id=current_task.id)  # Re-pointing the logs
                    )

            for item in task.worklogs:
                affected_dates.add(item.date)

                worklog_data = WorklogBase(
                    id=item.id,
                    date=item.date,
                    duration=item.duration,
                    activity_task_id=current_task.id,
                    user_id=user_id,
                )
                if worklog_data.id and worklog_data.duration is None:
                    to_delete.append(worklog_data)
                else:
                    to_upsert.append(worklog_data)

        await WorklogBase.delete_many(self.session, [Worklog.id.in_([item.id for item in to_delete])], commit=False)
        upsert_result = await WorklogBase.upsert_many(
            self.session, to_upsert, ["activity_task_id", "date", "user_id"], commit=False
        )

        return upsert_result, affected_dates

    async def batch_worklog(self, data: TaskBatchDto, user_id: UUID) -> List[WorklogBase]:
        """An employee will record their time (hours) spent on given tasks"""
        activity_ids: set[UUID] = {task.activity_id for task in data.tasks}
        worklogs_ids: set[UUID] = {worklog.id for task in data.tasks for worklog in task.worklogs if worklog.id}
        task_ids: set[UUID] = {task.id for task in data.tasks if task.id}

        await self._validate_activities(activity_ids, user_id)
        await self._validate_tasks(task_ids, user_id)
        await self._validate_worklogs(worklogs_ids, user_id)

        upsert_result, affected_dates = await self._process_worklogs(user_id, data)

        await self.session.flush()

        await self._cleanup_empty_tasks(user_id=user_id)
        await self._validate_worklogs_8_hours(user_id, affected_dates)

        await self.session.commit()
        logger.info(f"[JournalService]: Dates checked against: {affected_dates}")
        logger.info(f"[JournalService]: Worklog processing done: Upserted {len(upsert_result)} records.")

        return upsert_result

    async def get_journal(self, data: GetJournalDto, user_id: UUID) -> List[JournalActivity]:
        try:
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
                            ActivityTask.worklogs.any(Worklog.date.between(data.start_date, data.end_date)),
                        ),
                    ),
                    with_loader_criteria(
                        Worklog, and_(Worklog.user_id == user_id, Worklog.date.between(data.start_date, data.end_date))
                    ),
                )
            )
            result = (await self.session.scalars(stmt)).all()
            return [JournalActivity.from_activity_model(item) for item in result]
        except Exception as e:
            raise e
