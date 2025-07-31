from typing import Type, TypeVar, List, Optional, Any, Protocol, Union, Dict
from sqlmodel import SQLModel, select, Table, inspect, desc

from ..utils.set_logging import get_logger

# SQLAlchemy imports
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, InstrumentedAttribute
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import SQLAlchemyError


# helper class for type
class SQLModelTable(Protocol):
    __table__: Table
    __name__: str


T = TypeVar("T", bound=SQLModel)  # Bind to SQLModel or a subclass

logger = get_logger(__name__)


class BaseRepository:
    """
    Base class for data repositories providing common database interactions.
    """

    # ===============================
    #   CRUD base methods
    # ==============================

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _insert_data(
        self,
        *,
        model_class: Type[T],
        instances: Union[T, List[T]],
    ) -> bool:

        try:
            logger.info("Validating inputs...")

            validated_inputs = self._validate_input_types(model_class, instances)
            input_values = [instance.model_dump() for instance in validated_inputs]

            on_conflict_keys = self._get_primary_key_names(model_class)

            stmt = pg_insert(model_class).values(input_values).on_conflict_do_nothing(index_elements=on_conflict_keys)

            await self.session.execute(stmt)
            return True
        except SQLAlchemyError as e:
            logger.error(f"DB error encountered when attempting to insert data {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error when inserting data: {e}", exc_info=True)
            raise

    async def _upsert_data(
        self,
        *,
        model_class: Type[T],
        instances: Union[T, List[T]],
    ) -> bool:

        try:
            logger.info("Validating inputs...")

            validated_inputs = self._validate_input_types(model_class, instances)
            input_values = [instance.model_dump() for instance in validated_inputs]

            on_conflict_keys = self._get_primary_key_names(model_class)

            update_dict = self._get_update_excluded_dict(model_class)

            stmt = (
                pg_insert(model_class)
                .values(input_values)
                .on_conflict_do_update(index_elements=on_conflict_keys, set_=update_dict)
            )

            await self.session.execute(stmt)
            return True
        except SQLAlchemyError as e:
            logger.error(f"DB error encountered when attempting to insert data {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error when inserting data: {e}", exc_info=True)
            raise

    async def _get_data(
        self,
        *,
        model_class: Type[T],
        id_filters: Optional[List[int]] = None,
        relationships: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> List[T]:

        pk_attributes = self._get_primary_key_attribute(model_class)
        if len(pk_attributes) != 1:
            logger.warning(f"model {model_class} has more than 1 primary key")
            return []

        single_pk_attribute = pk_attributes[0]
        try:

            stmt = select(model_class)

            if id_filters:
                stmt = self._filter_by_ids(single_pk_attribute, id_filters, stmt)
            if relationships:
                stmt = self._add_relationships(model_class, relationships, stmt)
            if limit:
                stmt = stmt.limit(limit=limit)

            stmt = stmt.order_by(desc(single_pk_attribute))

            # Execute
            result = await self.session.execute(stmt.execution_options(populate_existing=True))
            instances = result.scalars().all()

            logger.info(f"Retrieved {len(instances)} records for {model_class.__name__}")
            return instances  # type: ignore
        except Exception as e:
            logger.error(f"Error records for {model_class.__name__}: {e}", exc_info=True)
            raise

    # ========================
    # Helper methods
    # ========================

    def _get_primary_key_attribute(self, model_class: Type[T]) -> List[InstrumentedAttribute[Any]]:
        """Helper to get the single primary key attribute of a model."""
        mapper = inspect(model_class)
        if mapper is None:
            raise ValueError(f"Unable to inspect model class {model_class.__name__}")
        pk_columns = mapper.primary_key

        pk_attributes = [getattr(model_class, col.name) for col in pk_columns]

        return pk_attributes

    def _get_primary_key_names(self, model_class: Type[T]) -> List[str]:
        mapper = inspect(model_class)
        if mapper is None:
            raise ValueError(f"Unable to inspect model class {model_class.__name__}")
        pk_columns = mapper.primary_key

        return [col.name for col in pk_columns]

    def _get_update_excluded_dict(self, model_class: Type[T]) -> Dict[str, Any]:

        pk_attr_names = {attr.key for attr in self._get_primary_key_attribute(model_class)}

        filtered_cols = [col_name for col_name in model_class.model_fields.keys() if col_name not in pk_attr_names]

        update_dict = {col: getattr(pg_insert(model_class).excluded, col) for col in filtered_cols}
        return update_dict

    def _filter_by_ids(self, pk_attribute: InstrumentedAttribute[Any], id_filters: List[int], stmt: Any) -> Any:

        if not id_filters:
            logger.warning("empty input list provided for id_filters")
            return stmt
        if not isinstance(id_filters, list):
            logger.warning(f"expected type list, got type {type(id_filters).__name__} for id_filters")
            return stmt

        stmt = stmt.where(pk_attribute.in_(id_filters))

        return stmt

    def _add_relationships(self, model_class: Type[T], relationships: List[str], stmt: Any) -> Any:

        if not relationships:
            logger.warning(f"No relationships, input: {relationships}")
            return stmt

        if not isinstance(relationships, list):
            logger.warning(f"expected type {type(list)}, got type {type(relationships)} for relationships")
            return stmt

        mapper = inspect(model_class)
        if mapper is None:
            raise ValueError(f"Unable to inspect model class {model_class.__name__}")
        valid_relationship_names = set(mapper.relationships.keys())

        for rel_name in relationships:
            if rel_name in valid_relationship_names:
                relationship_attribute = getattr(model_class, rel_name)
                stmt = stmt.options(selectinload(relationship_attribute))
            else:
                logger.warning(f"Relationship name '{rel_name}' not found in model" f"'{model_class.__name__}'")
        return stmt

    def _validate_input_types(self, model_class: Type[T], instances: Union[T, List[T]]) -> List[T]:
        if isinstance(instances, model_class):
            instances = [instances]
        elif isinstance(instances, list):
            for instance in instances:
                if not isinstance(instance, model_class):
                    logger.error(f"Expected input to be type{type(model_class)}, got type {type(instance)}")
                    raise ValueError(f"Incorrect input value type: {type(instance).__name__}")
        else:
            logger.error(
                f"Expected {model_class.__name__} or List[{model_class.__name__}], got {type(instances).__name__}"
            )
            raise TypeError(f"Invalid input type: {type(instances).__name__}")

        return instances
