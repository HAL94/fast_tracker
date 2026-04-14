from typing import ClassVar, Optional
from uuid import UUID

from pydantic import Field

from app.core.database.mixin import BaseModelDatabaseMixin
from app.models import Tenant


class TenantBase(BaseModelDatabaseMixin):
    model: ClassVar[Tenant] = Tenant

    id: Optional[UUID] = Field(default=None)
    organization_name: str
