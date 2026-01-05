from abc import ABC
from typing import Any, ClassVar, Dict, List, Literal, Optional, Self, TypeVar, Union

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.strategy_options import _AbstractLoad
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import NotFoundException
from app.core.pagination import PaginatedResult
from app.core.pagination.factory import PaginationQuery
from app.core.schema import BaseModel as AppBaseModel

from .base import Base

T = TypeVar(name="T", bound=Base)


class BaseModelDatabaseMixin[T](AppBaseModel, ABC):
    model: ClassVar[Base]

    @classmethod
    def relations(cls):
        return []

    @classmethod
    async def exists(
        cls,
        session: AsyncSession,
        val: Any,
        /,
        *,
        field: Optional[str] = None,
        raise_not_found: bool = False,
        where_clause: list[ColumnElement[bool]] = None,
    ) -> bool:
        try:
            result = await cls.model.exists(session, val, field=field, where_clause=where_clause)

            if raise_not_found and not result:
                raise NotFoundException(message=f"{cls.model.__name__} resource does exist")

            return result
        except Exception as e:
            raise e

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        data: BaseModel,
        /,
        *,
        commit: bool = True,
        return_as_base: bool = False,
    ) -> Union[Self | T]:
        try:
            result = await cls.model.create(session, data, commit=commit)

            if return_as_base:
                return result

            return cls.model_validate(result, from_attributes=True)
        except Exception as e:
            raise e

    @classmethod
    async def create_many(
        cls,
        session: AsyncSession,
        data: Union[list[BaseModel] | list[dict]],
        /,
        *,
        commit: bool = True,
        return_as_base: bool = False,
        batch_size: Optional[int] = 100,
    ) -> Union[list[Self], list[T]]:
        try:
            if not data or len(data) <= 0:
                return []

            result: list[Base] = await cls.model.create_many(session, data, commit=commit, batch_size=batch_size)

            if return_as_base:
                return result

            data = [cls.model_validate({**item.dict()}, from_attributes=True) for item in result]

            return data
        except Exception as e:
            raise e

    @classmethod
    async def update_one(
        cls,
        session: AsyncSession,
        data: BaseModel | dict,
        /,
        *,
        where_clause: list[ColumnElement[bool]] | None = None,
        commit: bool = True,
        return_as_base: bool = False,
    ) -> Union[Self, T]:
        try:
            result = await cls.model.update_one(session, data, where_clause=where_clause, commit=commit)

            if return_as_base:
                return result

            return cls.model_validate(result, from_attributes=True)
        except Exception as e:
            raise e

    @classmethod
    async def get_all(
        cls,
        session: AsyncSession,
        /,
        *,
        pagination: PaginationQuery | None = None,
        where_clause: list[ColumnElement[bool]] | None = [],
        order_clause: list[InstrumentedAttribute] | None = [],
        limit: Optional[int] = 20,
        options: list[_AbstractLoad] | None = None,
        return_as_base: bool = False,
    ) -> Union[List[Self], PaginatedResult[Union[Self, T]]]:
        try:
            if not options:
                options = cls.relations()

            if not pagination:
                result = await cls.model.get_all(
                    session,
                    where_clause=where_clause,
                    order_clause=order_clause,
                    options=options,
                    limit=limit,
                )

                if return_as_base:
                    return result

                return [cls.model_validate(item, from_attributes=True) for item in result]

            pagination_where_clause = pagination.filter_fields
            pagination_order_clause = pagination.sort_fields
            page = pagination.page
            size = pagination.size

            paginated_result = await cls.model.get_many(
                session,
                page=page,
                size=size,
                where_clause=where_clause + pagination_where_clause,
                order_clause=order_clause + pagination_order_clause,
                options=options,
            )
            if return_as_base:
                return paginated_result

            result = paginated_result.result
            paginated_result.result = [cls.model_validate(item, from_attributes=True) for item in result]

            return paginated_result

        except Exception as e:
            raise e

    @classmethod
    async def get_one(
        cls,
        session: AsyncSession,
        val,
        /,
        *,
        field: InstrumentedAttribute | None = None,
        where_clause: list[ColumnElement[bool]] | None = None,
        options: list[_AbstractLoad] | None = None,
        return_as_base: bool = False,
        raise_not_found: bool = True,
    ) -> Self | T | None:
        current_options = []
        current_options.extend(cls.relations())

        if options is not None:
            current_options.extend(options)

        result = await cls.model.get_one(
            session,
            val,
            field=field,
            where_clause=where_clause,
            options=current_options,
        )
        if not result and raise_not_found:
            raise NotFoundException
        if not result:
            return None

        if return_as_base:
            return result
        return cls.model_validate(result, from_attributes=True)

    @classmethod
    async def upsert_one(
        cls,
        session: AsyncSession,
        data: Union[dict, BaseModel],
        index_elements: list[InstrumentedAttribute | str] | None = None,
        /,
        *,
        commit: bool = True,
        return_as_base: bool = False,
        on_conflict: Literal["do_nothing", "do_update"] = "do_update",
    ) -> Union[Self, T]:
        if isinstance(data, dict):
            try:
                data = cls.model_validate(data, from_attributes=True)
            except Exception as e:
                raise e

        result = await cls.model.upsert_one(session, data, index_elements, commit=commit, on_conflict=on_conflict)

        if return_as_base:
            return result

        return cls.model_validate(result, from_attributes=True)

    @classmethod
    async def delete_one(
        cls,
        session: AsyncSession,
        val: Any,
        /,
        *,
        field: InstrumentedAttribute | None = None,
        where_clause: list[ColumnElement[bool]] = None,
        commit: bool = True,
        return_as_base: bool = False,
    ):
        try:
            result = await cls.model.delete_one(session, val, field=field, where_clause=where_clause, commit=commit)

            if return_as_base:
                return result

            if not result:
                raise NotFoundException()

            return cls.model_validate(result, from_attributes=True)
        except Exception as e:
            raise e

    @classmethod
    async def delete_many(
        cls,
        session: AsyncSession,
        where_clause: list[ColumnElement[bool]] = None,
        /,
        *,
        commit: bool = True,
        return_as_base: bool = False,
    ):
        try:
            result = await cls.model.delete_many(session, where_clause, commit=commit)

            if return_as_base:
                return result

            return [cls.model_validate(item, from_attributes=True) for item in result]
        except Exception as e:
            raise e

    @classmethod
    async def upsert_many(
        cls,
        session: AsyncSession,
        data: Union[list[dict] | list[BaseModel]],
        index_elements: list[InstrumentedAttribute | str] | None = None,
        /,
        *,
        commit: bool = True,
        return_as_base: bool = False,
        on_conflict: Literal["do_nothing", "do_update"] = "do_update",
    ) -> Union[list[Self] | list[type[Base]]]:
        if not data or len(data) == 0:
            return []

        if isinstance(data[0], dict):
            try:
                data = [cls.model_validate(item, from_attributes=True) for item in data]
            except Exception as e:
                raise e

        result = await cls.model.upsert_many(session, data, index_elements, commit=commit, on_conflict=on_conflict)

        if return_as_base:
            return result

        return [cls.model_validate(item, from_attributes=True) for item in result]

    @classmethod
    async def update_many_by_id(
        cls,
        session: AsyncSession,
        data: list[BaseModel],
        /,
        *,
        commit: bool = True,
        where_clause: Optional[list[ColumnElement[bool]]] = None,
        return_as_base: bool = False,
    ):
        try:
            result = await cls.model.update_many_by_id(session, data, commit=commit, where_clause=where_clause)

            if return_as_base:
                return result

            return [cls.model_validate(item, from_attributes=True) for item in result]
        except Exception as e:
            raise e

    @classmethod
    async def update_many_by_whereclause(
        cls,
        session: AsyncSession,
        data: Union[BaseModel, Dict[str, Any]],
        where_clause: list[ColumnElement[bool]],
        /,
        *,
        commit: bool = True,
    ):
        """
        Update multiple records based on a condition

        returns:
            None
        """
        try:
            await cls.model.update_many_by_whereclause(
                session,
                data,
                where_clause,
                commit=commit,
            )
            return None
        except Exception as e:
            raise e
