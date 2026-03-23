import uuid
from typing import Callable, List, Optional

from app.dto.journal import TaskBatchDto, UpsertActivityTask, WorklogDto

# size: Optional[int] = None, year: Optional[int] = None, month: Optional[int] = None
type WorklogFactoryFn = Callable[[], Callable[[Optional[int], Optional[int], Optional[int]], List[WorklogDto]]]
type TaskBatchFactoryFn = Callable[[], Callable[[List[uuid.UUID], List[WorklogDto]], TaskBatchDto]]
type TaskFactoryFn = Callable[
    [],
    Callable[
        [
            uuid.UUID,
            Optional[int],
            Optional[int],
            Optional[int],
            Optional[int],
            Optional[List[WorklogDto]],
            List[UpsertActivityTask],
        ]
    ],
]
