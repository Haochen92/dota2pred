from typing import Type, TypeVar, List, Optional, Any, Protocol
from sqlmodel import SQLModel, select, Table, inspect, desc
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from utils.set_logging import get_logger

# helper class for type
class SQLModelTable(Protocol):
    __table__: Table
    __name__: str
    
T = TypeVar("T", bound=SQLModel)

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

    async def _get_instance_by_id(self, model_class: Type[T], pk_value: Any) -> Optional[T]:
        """
        Retrieves a single record by id
        """

        mapper = inspect(model_class)
        pk_columns = mapper.primary_key
        
        if len(pk_columns) > 1:
            raise ValueError('model has more than 1 primary key')

        pk_col_name = pk_columns[0].name
        
        if not hasattr(model_class, pk_col_name):
            raise AttributeError(f'Missing Attribute for {pk_col_name} in {model_class.__name__}' )
        pk_attribute = getattr(model_class, pk_col_name)
            
            
        async with AsyncSession(self.engine) as session:
             try:
                stmt = select(model_class).where(pk_attribute == pk_value)
                result = await session.execute(stmt)
                instance = result.scalars().first()
                if instance:
                    logger.debug(f"Retrieved record for {model_class.__name__} with id {id}")
                else:
                    logger.debug(f"No record found for {model_class.__name__} with id {id}")
                    return None
                return instance
             except AttributeError:
                  logger.error(f"Missing id attribute from Model {model_class.__name__}", exc_info=True)
                  raise 
             except Exception as e:
                  logger.error(f"Error retrieving {model_class.__name__} by id {id}: {e}", exc_info=True)
                  return None