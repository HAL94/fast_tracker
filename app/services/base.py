from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.mixin import BaseModelDatabaseMixin


class BaseService(ABC):
    """
    Base service class providing common patterns for all services.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    @abstractmethod
    def _get_model(self) -> type[BaseModelDatabaseMixin]:
        """Return the model class this service works with."""
        pass

    @property
    def model(self) -> type[BaseModelDatabaseMixin]:
        """Get the model class."""
        return self._get_model()
