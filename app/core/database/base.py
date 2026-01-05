from datetime import datetime
from typing import Any, Callable, Dict, Literal, Optional, Self, Union, override

from asyncpg.exceptions import ForeignKeyViolationError, UniqueViolationError
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    DateTime,
    Select,
    delete,
    func,
    insert,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.inspection import Inspectable, inspect
from sqlalchemy.orm import (
    DeclarativeBaseNoMeta as _DeclarativeBaseNoMeta,
)
from sqlalchemy.orm import (
    Mapped,
    RelationshipProperty,
    mapped_column,
)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.decl_api import (
    DeclarativeAttributeIntercept as _DeclarativeAttributeIntercept,
)
from sqlalchemy.orm.strategy_options import Load, _AbstractLoad
from sqlalchemy.sql._typing import _HasClauseElement
from sqlalchemy.sql.elements import ColumnElement, SQLCoreOperations
from sqlalchemy.sql.roles import ColumnsClauseRole, TypedColumnsClauseRole

from app.core.pagination import PaginatedResult


class DeclarativeBaseNoMeta(_DeclarativeBaseNoMeta):
    pass


class DeclarativeAttributeIntercept(_DeclarativeAttributeIntercept):
    @property
    def select_(
        cls,  # noqa: N805
    ) -> Callable[
        [
            tuple[
                TypedColumnsClauseRole[Any]
                | ColumnsClauseRole
                | SQLCoreOperations[Any]
                | Inspectable[_HasClauseElement[Any]]
                | _HasClauseElement[Any]
                | Any,
                ...,
            ],
            dict[str, Any],
        ],
        Select[Any],
    ]:
        return select


class Base(DeclarativeBaseNoMeta, metaclass=DeclarativeAttributeIntercept):
    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(
            timezone=True,
        ),
        server_default=func.now(),
        nullable=False,
    )

    def dict(self):
        return self.__dict__

    @override
    def __repr__(self) -> str:
        return str(self.dict())

    @classmethod
    async def count(cls, session: AsyncSession, /) -> int:
        return await session.scalar(func.count(cls.id))

    @classmethod
    def get_select_in_load(cls) -> list[Load]:
        return []

    @classmethod
    def get_options(cls) -> list[Load]:
        return cls.get_select_in_load()

    @classmethod
    def get_relationships(cls) -> Dict[str, RelationshipProperty[Any]]:
        mapper = inspect(cls)
        relations = {rel[0]: rel[1] for rel in mapper.relationships.items()}
        return relations

    @classmethod
    def get_foreign_columns(cls) -> Dict[str, Column]:
        relations = cls.get_relationships()
        foreign_cols = {}
        for rel in relations:
            relationship_property: RelationshipProperty = relations[rel]
            for fk in relationship_property.remote_side:
                foreign_cols[rel] = fk.name

        return foreign_cols

    @classmethod
    def columns(cls):
        return {_column.name for _column in inspect(cls).c}

    @classmethod
    async def exists(
        cls,
        session: AsyncSession,
        val: Optional[Any] = None,
        /,
        *,
        field: Optional[str] = None,
        where_clause: list[ColumnElement[bool]] = None,
    ) -> bool:
        try:
            if not field:
                field = cls.id

            where_base = [field == val]

            if where_clause:
                where_base.extend(where_clause)

            stmt = select(cls).where(*where_base)

            result = await session.execute(stmt)

            result_scalar = result.scalar()

            print(f"Result scalar: {result_scalar}")

            return result_scalar is not None
        except Exception as e:
            raise e

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        data: Union[BaseModel, Dict],
        /,
        *,
        commit: bool = True,
    ):
        try:
            payload = data
            if isinstance(data, BaseModel):
                payload = data.model_dump(exclude_none=True, exclude_unset=True, by_alias=False)

            obj: Base = cls(**payload)

            session.add(obj)

            if commit:
                await session.commit()

            return obj
        except IntegrityError as e:
            await session.rollback()

            if e.orig.sqlstate == UniqueViolationError.sqlstate:
                raise ValueError("Unique Constraint is Violated")
            elif e.orig.sqlstate == ForeignKeyViolationError.sqlstate:
                raise ValueError("Foreig Key Constraint is violated")

            raise e

    @classmethod
    async def create_many(
        cls,
        session: AsyncSession,
        data: Union[list[BaseModel], list[Dict]],
        /,
        *,
        commit: bool = True,
        batch_size: Optional[int] = 100,
    ):
        try:
            if len(data) <= 0:
                return []
            payload = data

            statement = insert(cls).returning(cls)

            result = []
            for batch in range(0, len(data), batch_size):
                if isinstance(data[0], BaseModel):
                    payload = [
                        item.model_dump(exclude_unset=True, exclude_none=True, by_alias=False)
                        for item in data[batch : batch + batch_size]
                    ]
                insert_result = (await session.execute(statement, payload)).scalars().all()
                result.extend(insert_result)

            if commit:
                await session.commit()

            return result
        except IntegrityError as e:
            await session.rollback()
            raise e

    @classmethod
    async def get_many(
        cls,
        session: AsyncSession,
        /,
        *,
        page: int,
        size: int,
        where_clause: list[ColumnElement[bool]] | None = None,
        order_clause: list[InstrumentedAttribute] | None = None,
        options: list[_AbstractLoad] | None = None,
    ):
        try:
            statement = select(cls)
            where_base = []

            if where_clause:
                where_base.extend(where_clause)

            statement = statement.where(*where_base)

            if order_clause:
                statement = statement.order_by(*order_clause)

            total_count = await session.scalar(
                select(func.count()).select_from(select(cls).where(*where_base).subquery())
            )
            base_options = cls.get_select_in_load()
            if base_options:
                statement = statement.options(*base_options)

            if options:
                statement = statement.options(*options)

            statement = statement.offset((page - 1) * size).limit(size)

            result = await session.scalars(statement)

            return PaginatedResult(result=result, size=size, page=page, total_records=total_count)
        except Exception as e:
            raise e

    @classmethod
    async def get_all(
        cls,
        session: AsyncSession,
        /,
        *,
        where_clause: list[ColumnElement[bool]] = None,
        order_clause: list[InstrumentedAttribute] = [],
        limit: int = 20,
        options: list[_AbstractLoad] | None = None,
    ):
        try:
            statement = select(cls)
            where_base = []

            if where_clause:
                where_base.extend(where_clause)

            statement = statement.where(*where_base)

            if order_clause:
                statement = statement.order_by(*order_clause)

            base_options = cls.get_options()

            if base_options:
                statement = statement.options(*base_options)

            if options:
                statement = statement.options(*options)

            statement = statement.limit(limit)

            result = await session.scalars(statement)

            return result.all()
        except Exception as e:
            raise e

    @classmethod
    async def get_one(
        cls,
        session: AsyncSession,
        val: Any,
        /,
        *,
        field: InstrumentedAttribute | str | None = None,
        options: list[_AbstractLoad] = None,
        where_clause: list[ColumnElement[bool]] = None,
    ) -> Self:
        base_options = cls.get_options()

        if field is None:
            field = cls.id

        where_base = [field == val]

        if where_clause:
            where_base.extend(where_clause)

        statement: Select = cls.select_(cls).where(*where_base)

        if base_options:
            statement = statement.options(*base_options)

        if options:
            statement = statement.options(*options)

        result = await session.scalar(statement)

        return result

    @classmethod
    async def update_one(
        cls,
        session: AsyncSession,
        data: Union[BaseModel, Dict],
        /,
        *,
        where_clause: list[ColumnElement[bool]] | None = None,
        commit: bool = True,
    ):
        if not where_clause:
            raise ValueError("must pass where_clause")

        if isinstance(data, BaseModel):
            data = data.model_dump(exclude_unset=True, exclude_none=True, by_alias=False)

        updated_model = await session.scalar(update(cls).values(data).filter(*where_clause).returning(cls))

        if commit:
            await session.commit()

        return updated_model

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
    ):
        try:
            if field is None:
                field = cls.id

            if val is None:
                raise ValueError("Passed 'None' as 'val'")

            where_cond = [field == val]

            if where_clause:
                where_cond.extend(where_clause)

            result = await session.scalar(delete(cls).where(*where_cond).returning(cls))

            if commit:
                await session.commit()

            return result

        except IntegrityError as e:
            await session.rollback()

            if e.orig.sqlstate == UniqueViolationError.sqlstate:
                raise ValueError("Unique Constraint is Violated")
            elif e.orig.sqlstate == ForeignKeyViolationError.sqlstate:
                raise ValueError("Foreig Key Constraint is violated")

            raise e

    @classmethod
    async def delete_many(
        cls,
        session: AsyncSession,
        where_clause: list[ColumnElement],
        /,
        *,
        commit: bool = True,
    ):
        try:
            if not where_clause:
                raise ValueError("'where_cluse' must be passed")

            result = await session.scalars(delete(cls).where(*where_clause).returning(cls))

            if commit:
                await session.commit()

            result = result.all()

            return result
        except IntegrityError as e:
            await session.rollback()
            if e.orig.sqlstate == UniqueViolationError.sqlstate:
                raise ValueError("Unique Constraint is Violated")
            elif e.orig.sqlstate == ForeignKeyViolationError.sqlstate:
                raise ValueError("Foreig Key Constraint is violated")

            raise e

    @classmethod
    async def upsert_one(
        cls,
        session: AsyncSession,
        data: BaseModel,
        index_elements: list[InstrumentedAttribute | str] | None = None,
        /,
        *,
        commit: bool = True,
        on_conflict: Literal["do_nothing", "do_update"] = "do_update",
    ):
        try:
            if not index_elements:
                index_elements = ["id"]

            data_dict = data.model_dump(exclude_none=True, by_alias=False)

            data_keys = set(data_dict.keys())
            index_keys = set(index_elements)
            missing_keys = index_keys - data_keys

            if missing_keys:
                raise ValueError(f"Data must include all index elements. Missing: {missing_keys}")

            if len(data_keys - index_keys) == 0:
                raise ValueError("Index elements match all data fields, upsert is invalid.")

            stmt = pg_insert(cls).values(data_dict)

            if on_conflict == "do_update":
                updated_columns = {
                    key: getattr(stmt.excluded, key) for key in data_dict.keys() if key not in index_elements
                }

                stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=updated_columns)
            else:
                stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)

            result = await session.scalar(stmt.returning(cls))

            if commit:
                await session.commit()

            return result
        except IntegrityError as e:
            await session.rollback()

            if e.orig.sqlstate == UniqueViolationError.sqlstate:
                raise ValueError("Unique Constraint is Violated")
            elif e.orig.sqlstate == ForeignKeyViolationError.sqlstate:
                raise ValueError("Foreig Key Constraint is violated")

            raise e

    @classmethod
    async def upsert_many(
        cls,
        session: AsyncSession,
        data: list[BaseModel],
        index_elements: list[InstrumentedAttribute | str] | None = None,
        /,
        *,
        commit: bool = True,
        on_conflict: Literal["do_nothing", "do_update"] = "do_update",
    ):
        try:
            if not index_elements:
                index_elements = [cls.id]

            index_elements = [
                col.name if isinstance(col, InstrumentedAttribute) else str(col) for col in index_elements
            ]
            data_values = [item.model_dump(exclude_none=True, by_alias=False) for item in data]

            data_model_fields = data[0].__class__.model_fields
            data_keys = set(data_model_fields.keys())
            index_keys = set(index_elements)

            # if all keys in data match with index_elements, then the operation is invalid
            # because there are no distinctions that could be used for the on conflict clause.
            if len(data_keys - index_keys) == 0:
                raise ValueError("Index elements match all model fields, upsert is invalid.")
            #  if no key in index_elements exists in data, then the operation is invalid
            missing_keys = index_keys - data_keys
            if missing_keys:
                raise ValueError(
                    f"Data passed must include the indexed_elements to handle conflicts. Missing: {missing_keys}"
                )

            stmt = pg_insert(cls).values(data_values)

            if on_conflict == "do_nothing":
                stmt = stmt.on_conflict_do_nothing(index_elements=index_elements)
            else:
                updated_columns = {
                    key: getattr(stmt.excluded, key)
                    # Use the first data object's keys
                    for key in data_values[0].keys()
                    if key not in index_elements  # Ensure index elements are not updated
                }
                stmt = stmt.on_conflict_do_update(index_elements=index_elements, set_=updated_columns)

            updated_or_created_data = await session.scalars(
                stmt.returning(cls),
                execution_options={"populate_existing": True},
            )

            if commit:
                await session.commit()

            result = updated_or_created_data.all()

            return result
        except IntegrityError as e:
            await session.rollback()

            if e.orig.sqlstate == UniqueViolationError.sqlstate:
                raise ValueError("Unique Constraint is Violated")
            elif e.orig.sqlstate == ForeignKeyViolationError.sqlstate:
                raise ValueError("Foreig Key Constraint is violated")

            raise e

    @classmethod
    async def update_many_by_id(
        cls,
        session: AsyncSession,
        data: list[BaseModel],
        /,
        *,
        commit: bool = True,
        where_clause: Optional[list[ColumnElement[bool]]] = None,
    ):
        """Update several records"""
        try:
            if data is None:
                raise ValueError("Data passed cannot be None")

            if isinstance(data, list) and len(data) == 0:
                return []

            fields = data[0].model_fields_set

            if "id" not in fields:
                raise ValueError("Primary Key 'id' not found in fields of passed list")

            if not where_clause:
                where_clause = []

            stmt = update(cls).where(*where_clause)

            update_ids = []
            update_items = []

            for item in data:
                update_items.append(item.model_dump(exclude_none=True, by_alias=False))
                update_ids.append(getattr(item, "id"))

            await session.execute(stmt, update_items, execution_options={"synchronize_session": None})

            if commit:
                await session.commit()

            return await session.scalars(select(cls).where(cls.id.in_(update_ids)))
        except IntegrityError as e:
            await session.rollback()

            if e.orig.sqlstate == UniqueViolationError.sqlstate:
                raise ValueError("Unique Constraint is Violated")
            elif e.orig.sqlstate == ForeignKeyViolationError.sqlstate:
                raise ValueError("Foreig Key Constraint is violated")

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
    ) -> None:
        try:
            if isinstance(data, BaseModel):
                data = data.model_dump(exclude_none=True, by_alias=False)

            stmt = update(cls).where(*where_clause).values(**data)

            await session.execute(stmt)

            if commit:
                await session.commit()

            return None
        except IntegrityError as e:
            await session.rollback()

            if e.orig.sqlstate == UniqueViolationError.sqlstate:
                raise ValueError("Unique Constraint is Violated")
            elif e.orig.sqlstate == ForeignKeyViolationError.sqlstate:
                raise ValueError("Foreig Key Constraint is violated")

            raise e
