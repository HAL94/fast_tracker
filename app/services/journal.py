import logging
from datetime import date as Date
from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.activity_task import ActivityTaskBase
from app.domain.worklog import WorklogBase
from app.dto.journal import GetJournalDto, JournalActivity, TaskBatchDto, UpsertActivityTask
from app.models import Worklog
from app.repositories.journal_repository import JournalRepository
from app.services.base import BaseService

logger = logging.getLogger("uvicorn.info")
logger.setLevel(logging.INFO)


class JournalService(BaseService):
    def __init__(self, session: AsyncSession):
        self._journal_repo = JournalRepository(session=session)

    async def _fork_or_upsert_task(self, task: UpsertActivityTask, user_id: UUID, tenant_id: UUID) -> ActivityTaskBase:
        """Attempt to determine create or update the task (upsert). If the client-side intention is an update of current
        task, then copy (fork) the task and point the worklogs to newly created task"""
        task_data = ActivityTaskBase(
            title=task.title,
            activity_id=task.activity_id,
            user_id=user_id,
            tenant_id=tenant_id,
            updated_at=datetime.now(),
        )
        index_elements = ["title", "activity_id", "user_id"]

        # upsert the task based on triplet index
        task_repo = self._journal_repo.get_task_repository()
        task_upsert_results = await task_repo.upsert([task_data], index_elements)
        current_task = task_upsert_results[0]

        # if the task id exists, then client wishes to update current task, they may also include worklogs
        if task.id and task.id != current_task.id:
            worklog_ids = [worklog.id for worklog in task.worklogs if worklog.id]

            if len(worklog_ids) > 0:
                # MOVE the logs to new task
                worklog_repo = self._journal_repo.get_worklog_repository()
                await worklog_repo.update({"activity_task_id": current_task.id}, [Worklog.id.in_(worklog_ids)])
        return current_task

    async def _process_worklogs(
        self, user_id: UUID, data: TaskBatchDto, tenant_id: UUID
    ) -> tuple[list[WorklogBase], set[datetime]]:
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
            current_task = await self._fork_or_upsert_task(task, user_id, tenant_id)

            for item in task.worklogs:
                affected_dates.add(item.date)

                worklog_data = WorklogBase(
                    id=item.id,
                    date=item.date,
                    duration=item.duration,
                    activity_task_id=current_task.id,
                    user_id=user_id,
                    tenant_id=tenant_id,
                )
                if worklog_data.id and worklog_data.duration is None:
                    to_delete.append(worklog_data)
                else:
                    to_upsert.append(worklog_data)

        worklog_repo = self._journal_repo.get_worklog_repository()
        await worklog_repo.delete([Worklog.id.in_([item.id for item in to_delete])])
        upsert_result = await worklog_repo.upsert(to_upsert, ["activity_task_id", "date", "user_id"])

        return upsert_result, affected_dates

    async def batch_worklog(self, data: TaskBatchDto, user_id: UUID, tenant_id: UUID) -> List[WorklogBase]:
        """An employee will record their time (hours) spent on given tasks"""
        activity_ids: set[UUID] = {task.activity_id for task in data.tasks}
        worklogs_ids: set[UUID] = {worklog.id for task in data.tasks for worklog in task.worklogs if worklog.id}
        task_ids: set[UUID] = {task.id for task in data.tasks if task.id}

        await self._journal_repo.validate_activities(activity_ids, user_id, tenant_id)
        await self._journal_repo.validate_tasks(task_ids, user_id, tenant_id)
        await self._journal_repo.validate_worklogs(worklogs_ids, user_id, tenant_id)

        upsert_result, affected_dates = await self._process_worklogs(user_id, data, tenant_id)

        await self._journal_repo.session.flush()

        await self._journal_repo.cleanup_empty_tasks(user_id, tenant_id)
        await self._journal_repo.validate_daily_worklog_hours(user_id, affected_dates, tenant_id)

        await self._journal_repo.session.commit()
        logger.info(f"[JournalService]: Dates checked against: {affected_dates}")
        logger.info(f"[JournalService]: Worklog processing done: Upserted {len(upsert_result)} records.")

        return upsert_result

    async def get_journal(self, data: GetJournalDto, user_id: UUID, tenant_id: UUID) -> List[JournalActivity]:
        return await self._journal_repo.get_journal(data, user_id, tenant_id)
