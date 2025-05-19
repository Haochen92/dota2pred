from typing import Type, TypeVar, List, Optional, Any, Protocol
from sqlmodel import SQLModel, select, Table, inspect, desc
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from src.utils.set_logging import get_logger

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
        
    
    async def _get_all_data_by_class(self, model_class: Type[T]) -> List[T]:
        """
        Retrieves all records for a given model class.

        Args:
            model_class: The SQLModel class to retrieve records for.

        Returns:
            A list of SQLModel instances. Returns empty list if none found or error.
        """
        async with AsyncSession(self.engine) as session:
            try:
                stmt = select(model_class)
                if hasattr(model_class, 'match_id'):
                    stmt = stmt.order_by(desc(model_class.match_id))
                    
                result = await session.execute(stmt)
                instances = result.scalars().all()
                logger.debug(f"Retrieved {len(instances)} records for {model_class.__name__}")
                return instances
            except Exception as e:
                logger.error(f"Error retrieving all records for {model_class.__name__}: {e}", exc_info=True)
                return [] 
            
    def _get_primary_key_attribute(self, model_class: Type[T]):
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

    async def _get_instance_by_id(self, model_class: Type[T], pk_value: Any) -> Optional[T]:
        """
        Retrieves a single record by its primary key value.
        Assumes a single primary key column.
        """
        try:
            pk_attribute = self._get_primary_key_attribute(model_class)

            async with AsyncSession(self.engine) as session:
                stmt = select(model_class).where(pk_attribute == pk_value)
                result = await session.execute(stmt)
                instance = result.scalars().first()

                if instance:
                    logger.debug(f"Retrieved record for {model_class.__name__} with pk {pk_value}")
                else:
                    logger.debug(f"No record found for {model_class.__name__} with pk {pk_value}")
                return instance 

        except (AttributeError, ValueError) as e: 
             logger.error(f"Error determining primary key for {model_class.__name__}: {e}", exc_info=True)
             raise 
        except Exception as e:
             logger.error(f"Error retrieving {model_class.__name__} by pk {pk_value}: {e}", exc_info=True)
             raise e


    async def _get_instances_by_batch_ids(self, model_class: Type[T], batch_ids: List[Any]) -> List[T]:
        """
        Retrieves multiple records by a list of primary key values.
        Assumes a single primary key column. Returns an empty list if no matches or on error.
        """
        # Handle empty input list efficiently
        if not batch_ids:
            logger.debug(f"Received empty batch ID list for {model_class.__name__}. Returning empty list.")
            return []

        try:
            pk_attribute = self._get_primary_key_attribute(model_class)

            async with AsyncSession(self.engine) as session:
                # Use the .in_() operator for the WHERE clause
                stmt = select(model_class).where(pk_attribute.in_(batch_ids))
                result = await session.execute(stmt)
                instances = result.scalars().all()

                logger.debug(f"Retrieved {len(instances)} records for {model_class.__name__} matching batch IDs.")
                return list(instances)

        except (AttributeError, ValueError) as e: # Catch PK detection errors
             logger.error(f"Error determining primary key for {model_class.__name__}: {e}", exc_info=True)
             return []
        except Exception as e:
             logger.error(f"Error retrieving {model_class.__name__} by batch IDs: {e}", exc_info=True)
             raise e