from pydantic import Field

from app.core.schema import BaseModel


class UpsertReportingPeriodDto(BaseModel):
    month: int = Field(min=1, max=12)
    year: int
