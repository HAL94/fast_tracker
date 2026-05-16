from typing import Any, ClassVar, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.base import BaseDomain
from app.models import Tenant, TenantConfig


class TenantBase(BaseDomain[Tenant]):
    model: ClassVar[Tenant] = Tenant

    id: Optional[UUID] = Field(default=None)
    organization_name: str




class TenantSettings(BaseModel):
    weekend_days: list[int]
    daily_limit_hours: float
    ramadan_limit_hours: float
    is_ramadan_mode: bool = False
    lock_after_days: int = 7  # Prevent editing logs older than a week


class TenantConfigBase(BaseDomain[TenantConfig]):
    model: ClassVar[TenantConfig] = TenantConfig

    id: Optional[UUID] = Field(default=None)
    tenant_id: UUID

    settings: dict[str, Any]
