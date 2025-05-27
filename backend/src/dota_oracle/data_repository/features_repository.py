from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from .base_repository import BaseRepository, T
from sqlmodel import SQLModel
from dota_oracle.utils.set_logging import get_logger
from typing import Optional, List, Type

logger = get_logger(__name__)

class FeaturesRepository(BaseRepository):
    """
    Repository class for handling database operations related to
    match features (Hero, Team, Player-Hero).
    Uses asynchronous SQLAlchemy Core and targets PostgreSQL.
    Returns SQLModel instances or lists thereof.
    """
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)

    async def _batch_upsert(
        self,
        table_class: Type[T],
        records: List[T],
        session: AsyncSession
    ) -> int:
        """
        Performs a batch upsert operation for the given records into the specified table.
        Returns the number of records attempted to upsert.
        """
        if not records:
            logger.warning(f"No records provided for batch upsert into {table_class.__name__}")
            return 0
        
        if not issubclass(table_class, SQLModel):
            raise ValueError(f"feature_table_class must be a subclass of SQLModel")

        sql_table = table_class.__table__ # type: ignore
        table_name = table_class.__name__

        try:
            primary_keys = [pk.name for pk in sql_table.primary_key.columns]
            if not primary_keys:
                 raise ValueError(f"Table {table_name} does not have a primary key defined for upsert.")

            update_cols = {c.name for c in sql_table.columns if c.name not in primary_keys}
            
            '''
            
            '''
            update_dict = {
                col_name: getattr(insert(sql_table).excluded, col_name)
                for col_name in update_cols
            }
            
            records_dict = [record.model_dump() for record in records]

            stmt = insert(sql_table).values(records_dict).on_conflict_do_update(
                index_elements=primary_keys,
                set_=update_dict
            )

            await session.execute(stmt)
            logger.info(f"Batch upsert statement executed for {len(records)} input records into {table_name}.")

            return len(records) 
        except Exception as e:
            logger.error(f"Error during batch upsert into {table_name}: {str(e)}", exc_info=True)
            raise


    async def store_features(
        self,
        feature_instances: List[T],
        table_class: Type[T]
    ) -> None:
        """
        Stores features from a DataFrame into the specified table using batch upsert.
        Converts DataFrame rows to dictionaries for storage.
        """
        if not feature_instances:
            logger.warning(f"Received empty list for storing features in {table_class.__name__}. Skipping.")
            return

        async with AsyncSession(self.engine, expire_on_commit=False) as session: 
            async with session.begin(): 
                try:
                    await self._batch_upsert(
                        session=session,
                        table_class=table_class,
                        records=feature_instances,
                    )
                except Exception as e:
                     raise e


    async def get_feature_by_id(self, match_id: int, feature_table_class: Type[T])-> Optional[T]:
        """
        Retrieves a single feature model instance by its primary key (assumed to be 'match_id').

        Args:
            match_id: The primary key value (match_id).
            feature_table_class: The SQLModel table class (e.g., HeroFeaturesTable).

        Returns:
            An optional SQLModel instance of type T, or None if not found.
        """
        if not match_id:
            raise ValueError(f"missing match_id")
        
        if not feature_table_class:
            raise ValueError(f"missing feature_table_class")
        
        if not issubclass(feature_table_class, SQLModel):
            raise ValueError(f"feature_table_class must be a subclass of SQLModel")    
        
        try:
            feature_instance: Optional[T] = await self._get_instance_by_id(feature_table_class, match_id)

            if not feature_instance:
                logger.debug(f"No feature found for table {feature_table_class.__name__}, match_id: {match_id}")
                return None

            logger.debug(f"Found feature for table {feature_table_class.__name__}, match_id: {match_id}")
            return feature_instance
        except Exception as e:
            logger.error(f"Error fetching feature from {feature_table_class.__name__} for match_id {match_id}: {e}", exc_info=True)
            raise

    async def get_all_features_from_table(self, feature_table_class: Type[T]) -> List[T]:
        """
        Retrieves all feature model instances from the specified table.

        Args:
            feature_table_class: The SQLModel table class (e.g., HeroFeaturesTable).

        Returns:
            A list of SQLModel instances of type T. Returns empty list if table is empty or on error.
        """
        if not feature_table_class:
            raise ValueError(f"Missing table_feature_class input")
        
        if not issubclass(feature_table_class, SQLModel):
            raise ValueError(f"feature_table_class must be a subclass of SQLModel")
        try:
            list_instances: List[T] = await self._get_all_data_by_class(feature_table_class)

            if not list_instances:
                logger.debug(f"No features found in table {feature_table_class.__name__}")
                return []

            logger.debug(f"Retrieved {len(list_instances)} features from table {feature_table_class.__name__}")
            return list_instances
        except Exception as e:
            logger.error(f"Error fetching all features from {feature_table_class.__name__}: {e}", exc_info=True)
            raise