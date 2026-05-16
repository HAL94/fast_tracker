from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tenant import TenantBase, TenantConfigBase, TenantSettings
from app.models import Tenant, TenantConfig
from app.repositories.base_repository import BaseRepository
from app.repositories.tenant_config_repository import TenantConfigRepository


class TenantRepository(BaseRepository[TenantBase, Tenant]):
    __model__ = Tenant

    def __init__(self, session: AsyncSession):
        self.tenant_config_repo = TenantConfigRepository(session)
        super().__init__(session)

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return TenantBase.model_validate(data, from_attributes=True)

    async def get_config(self, tenant_id: UUID) -> Optional[TenantConfigBase]:
        return await self.tenant_config_repo.get_one_or_none([TenantConfig.tenant_id == tenant_id])

    async def set_config(
        self, tenant_settings: TenantSettings, tenant_id: UUID, commit: bool = False
    ) -> TenantConfigBase:
        try:
            result = await self.tenant_config_repo.upsert(
                [TenantConfigBase(tenant_id=tenant_id, settings=tenant_settings.model_dump())],
                ["tenant_id"],
                commit=commit,
            )

            return result[0]
        except Exception as e:
            raise e
