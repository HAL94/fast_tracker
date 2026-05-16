from app.domain.tenant import TenantConfigBase
from app.models import TenantConfig
from app.repositories.base_repository import BaseRepository


class TenantConfigRepository(BaseRepository[TenantConfigBase, TenantConfig]):
    __model__ = TenantConfig

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return TenantConfigBase.model_validate(data, from_attributes=True)
