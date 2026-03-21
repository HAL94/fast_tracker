import uuid
from datetime import date as Date
from typing import Callable

from app.domain.activity import ActivityBase
from app.dto.activity import TaskBatchDto

type WorklogFactoryFn = Callable[[uuid.UUID, ActivityBase], Callable[[int, Date], TaskBatchDto]]
