from app.domain.activity_task import ActivityTaskBase
from app.models import ActivityTask
from app.repositories.base_repository import BaseRepository


class ActivityTaskRepository(BaseRepository[ActivityTaskBase, ActivityTask]):
    __model__ = ActivityTask

    def domain_model(self, data, as_domain = None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return ActivityTaskBase.model_validate(data, from_attributes=True)
