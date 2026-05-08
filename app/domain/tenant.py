from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.domain.base import BaseDomain
from app.models import Tenant


class TenantBase(BaseDomain[Tenant]):
    model: ClassVar[Tenant] = Tenant

    id: Optional[UUID] = Field(default=None)
    organization_name: str
