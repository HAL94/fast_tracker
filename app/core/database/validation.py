from .base import Base


def is_pydantic_database_mixin(obj) -> bool:
    """Check if object is a BaseModelDatabaseMixin instance using duck typing"""
    if hasattr(obj, "model"):
        return issubclass(obj.model, Base)
    return False
