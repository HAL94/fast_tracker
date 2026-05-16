from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, exists, not_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload, with_loader_criteria

from app.domain.activity_task import ActivityTaskBase
from app.dto.journal import GetJournalDto, JournalActivity, UpsertActivityTask
from app.models import Activity, ActivityTask, ActivityUser, Worklog
from app.repositories.task_repository import ActivityTaskRepository
from app.repositories.tenant_repository import TenantRepository
from app.repositories.worklog_repository import WorklogRepository


class JournalRepository:
    """
    Repository for journal-related data access operations.
    Handles validation, aggregation, and retrieval of journal data.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._task_repo = ActivityTaskRepository(session)
        self._worklog_repo = WorklogRepository(session)
        self._tenant_repo = TenantRepository(session)

    async def cleanup_empty_tasks(self, user_id: UUID, tenant_id: UUID) -> None:
        """
        Find and delete any activity tasks for a given user that do not have any worklogs.

        Arguments:
            `user_id`: the user ID
            `tenant_id`: the tenant ID
        """
        subq = not_(exists().where(Worklog.activity_task_id == ActivityTask.id))

        stmt = (
            delete(ActivityTask).where(ActivityTask.user_id == user_id, ActivityTask.tenant_id == tenant_id).where(subq)
        )

        await self.session.execute(stmt)

    async def fork_or_upsert_task(self, task: UpsertActivityTask, user_id: UUID, tenant_id: UUID) -> ActivityTaskBase:
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
        task_upsert_results = await self._task_repo.upsert([task_data], index_elements)
        current_task = task_upsert_results[0]

        # if the task id exists, then client wishes to update current task, they may also include worklogs
        if task.id and task.id != current_task.id:
            worklog_ids = [worklog.id for worklog in task.worklogs if worklog.id]

            if len(worklog_ids) > 0:
                # MOVE the logs to new task
                await self._worklog_repo.update({"activity_task_id": current_task.id}, [Worklog.id.in_(worklog_ids)])
        return current_task

    async def get_journal(self, data: GetJournalDto, user_id: UUID, tenant_id: UUID) -> list[JournalActivity]:
        """
        Retrieve journal activities for a user within a date range.

        Arguments:
            `data`: GetJournalDto with start_date and end_date
            `user_id`: the user ID
            `tenant_id`: the tenant ID

        Returns:
            list of JournalActivity objects
        """
        try:
            stmt = (
                select(Activity)
                .join(Activity.user_activities)
                .where(
                    Activity.tenant_id == tenant_id,
                    ActivityUser.user_id == user_id,
                    ActivityUser.tenant_id == tenant_id,
                )
                .options(
                    joinedload(Activity.activity_type),
                    selectinload(Activity.tasks).selectinload(ActivityTask.worklogs),
                    with_loader_criteria(
                        ActivityTask,
                        and_(
                            ActivityTask.user_id == user_id,
                            ActivityTask.tenant_id == tenant_id,
                            ActivityTask.worklogs.any(Worklog.date.between(data.start_date, data.end_date)),
                        ),
                    ),
                    with_loader_criteria(
                        Worklog,
                        and_(
                            Worklog.user_id == user_id,
                            Worklog.tenant_id == tenant_id,
                            Worklog.date.between(data.start_date, data.end_date),
                        ),
                    ),
                )
            )
            result = (await self.session.scalars(stmt)).all()
            return [JournalActivity.from_activity_model(item) for item in result]
        except Exception as e:
            raise e

    def get_task_repository(self) -> ActivityTaskRepository:
        """Get the task repository for task-specific operations."""
        return self._task_repo

    def get_worklog_repository(self) -> WorklogRepository:
        """Get the worklog repository for worklog-specific operations."""
        return self._worklog_repo

    def get_tenant_repository(self) -> TenantRepository:
        """Get the tenant repository for worklog-specific operations."""
        return self._tenant_repo
