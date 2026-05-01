from typing import Optional

from pydantic import BaseModel

from app.domain.worklog import WorklogBase
from app.models import Worklog
from app.repositories.base_repository import BaseRepository


class WorklogRepository(BaseRepository[WorklogBase, Worklog]):
    __model__ = Worklog

    def domain_model(self, data, as_domain: Optional[BaseModel] = None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return WorklogBase.model_validate(data, from_attributes=True)
