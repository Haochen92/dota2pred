from typing import Type, TypeVar, List, Optional, Any, Protocol
from sqlmodel import SQLModel, select, Table, inspect, desc
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from dota_oracle.utils.set_logging import get_logger
from sqlalchemy.orm import selectinload 
from sqlalchemy import Select

# helper class for type
class SQLModelTable(Protocol):
    __table__: Table
    __name__: str
    
T = TypeVar("T", bound=SQLModel) # Bind to SQLModel or a subclass 

logger = get_logger(__name__)

class BaseRepository:
    """
    Base class for data repositories providing common database interactions.
    """
    def __init__(self, engine: AsyncEngine):
        if engine is None:
            raise ValueError("Missing Database Engine")
        self.engine = engine
        
    async def _get_data(
        self,
        *,
        model_class: Type[T],
        id_filters: Optional[List[int]] = None,
        relationships: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ):
        async with AsyncSession(self.engine) as session:
            pk_attribute = self._get_primary_key_attribute(model_class)
            
            try:
                stmt = select(model_class)
                if id_filters:
                    stmt = self._filter_by_ids(pk_attribute, id_filters, stmt) 
                if relationships:
                    stmt = self._add_relationships(model_class, relationships, stmt)
                if limit:
                    stmt = stmt.limit(limit=limit)
                
                stmt = stmt.order_by(desc(pk_attribute))
                
                # Execute 
                result = await session.execute(stmt)
                instances = result.scalars().all()
                
                logger.info(f"Retrieved {len(instances)} records for {model_class.__name__}")
                return instances # type: ignore
            except Exception as e:
                logger.error(f"Error records for {model_class.__name__}: {e}", exc_info=True)
                raise
            
    def _get_primary_key_attribute(self, model_class: Type[T]) -> Any:
        """Helper to get the single primary key attribute of a model."""
        mapper = inspect(model_class)
        pk_columns = mapper.primary_key

        if len(pk_columns) != 1:
            raise ValueError(f'Model {model_class.__name__} must have exactly one primary key column.')

        pk_col_name = pk_columns[0].name

        if not hasattr(model_class, pk_col_name):
            raise AttributeError(f'Model {model_class.__name__} missing inspected primary key attribute {pk_col_name}')

        pk_attribute = getattr(model_class, pk_col_name)
        return pk_attribute
                    
                    
    def _filter_by_ids(self, pk_attribute: Any, id_filters: List[int], stmt: Select):
        
        if not id_filters:
            logger.warning("empty input list provided for id_filters")
            return stmt
        if not isinstance(id_filters, list):
            logger.warning(f"expected type list, got type {type(id_filters)} for id_filters")
            return stmt
        
        
        stmt = stmt.where(pk_attribute.in_(id_filters))
        
        return stmt

            
    def _add_relationships( self, model_class: Type[T], relationships: List[str], stmt: Select) -> Select:
        
        if not relationships:
            logger.warning(f"No relationships, input: {relationships}")
            return stmt
        
        if not isinstance(relationships, list):
            logger.warning(f"expected type {type(list)}, got type {type(relationships)} for relationships")
            return stmt
        
        mapper = inspect(model_class)
        valid_relationship_names = set(mapper.relationships.keys())
        
        for rel_name in relationships:
            if rel_name in valid_relationship_names:
                relationship_attribute = getattr(model_class, rel_name)
                stmt = stmt.options(selectinload(relationship_attribute))
            else:
                logger.warning(
                    f"Relationship name '{rel_name}' not found in model"
                    f"'{model_class.__name__}'"
                )
        return stmt
   