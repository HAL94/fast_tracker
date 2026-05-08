from app.domain.tenant import TenantBase
from app.models import Tenant
from app.repositories.base_repository import BaseRepository


class TenantRepository(BaseRepository[TenantBase, Tenant]):
    __model__ = Tenant

    def domain_model(self, data, as_domain=None):
        if as_domain:
            return as_domain.model_validate(data, from_attributes=True)
        return TenantBase.model_validate(data, from_attributes=True)
