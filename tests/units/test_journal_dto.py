from datetime import date as Date
from uuid import uuid4

import pytest

from app.core.exceptions import UnprocessableInputException
from app.dto.journal import UpsertActivityTask, WorklogDto


class TestJournalDtoValidations:
    def test_upsert_activity_task(self):
        """
        The Goal: Ensure Pydantic catches worklog in the current month being
        added to the next month of a Task BEFORE it hits the service.
        """
        worklog_item = WorklogDto(date=Date(2026, 3, 31), duration=4)  # March 31st!
        assertion_text = ""
        with pytest.raises(UnprocessableInputException) as excinfo:
            UpsertActivityTask(
                title="April Consultancy",
                month=4,  # April
                year=2026,
                activity_id=uuid4(),
                worklogs=[worklog_item],
            )
        assertion_text = f"Worklogs contain a date at {worklog_item.date} that is not within"  # noqa: E501
        assert assertion_text in str(excinfo.value)

    def test_worklog_date_matching_task_period_passes(self):
        """
        Goal: when the worklog month matches the task's month, then the test should succeed
        """
        worklog_item = WorklogDto(date=Date(2026, 4, 30), duration=4)
        UpsertActivityTask(
            title="April Consultancy",
            month=4,  # April
            year=2026,
            activity_id=uuid4(),
            worklogs=[worklog_item],
        )
