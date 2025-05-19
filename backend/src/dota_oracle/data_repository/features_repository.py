import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from .base_repository import BaseRepository, SQLModelTable, T
from dota_oracle.utils.set_logging import get_logger
from typing import Optional, List, Dict, Any, Type, cast

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
        table_class: Type[SQLModelTable],
        records: List[Dict[str, Any]],
        session: AsyncSession
    ) -> int:
        """
        Performs a batch upsert operation for the given records into the specified table.
        Returns the number of records attempted to upsert.
        """
        if not records:
            logger.warning(f"No records provided for batch upsert into {table_class.__name__}")
            return 0

        sql_table = table_class.__table__
        table_name = table_class.__name__

        try:
            primary_keys = [pk.name for pk in sql_table.primary_key.columns]
            if not primary_keys:
                 raise ValueError(f"Table {table_name} does not have a primary key defined for upsert.")

            update_cols = {c.name for c in sql_table.columns if c.name not in primary_keys}

            update_dict = {
                col_name: getattr(insert(sql_table).excluded, col_name)
                for col_name in update_cols
            }

            stmt = insert(sql_table).values(records).on_conflict_do_update(
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
        feature_dataframe: pd.DataFrame,
        table_class: Type[SQLModelTable]
    ) -> None:
        """
        Stores features from a DataFrame into the specified table using batch upsert.
        Converts DataFrame rows to dictionaries for storage.
        """
        if feature_dataframe.empty:
            logger.warning(f"Received empty DataFrame for storing features in {table_class.__name__}. Skipping.")
            return
        feature_records_from_df = feature_dataframe.to_dict(orient='records')
        feature_records = cast(List[Dict[str, Any]], feature_records_from_df)

        async with AsyncSession(self.engine, expire_on_commit=False) as session: 
            async with session.begin(): 
                try:
                    await self._batch_upsert(
                        session=session,
                        table_class=table_class,
                        records=feature_records,
                    )
                except Exception as e:
                     raise e


    async def get_feature_by_id(self, match_id: int, feature_table_class: Type[T])-> Optional[T]|Exception:
        """
        Retrieves a single feature model instance by its primary key (assumed to be 'match_id').

        Args:
            match_id: The primary key value (match_id).
            feature_table_class: The SQLModel table class (e.g., HeroFeaturesTable).

        Returns:
            An optional SQLModel instance of type T, or None if not found.
        """
        try:
            feature_instance: Optional[T] = await self._get_instance_by_id(feature_table_class, match_id)

            if not feature_instance:
                logger.warning(f"No feature found for table {feature_table_class.__name__}, match_id: {match_id}")
                return None

            logger.debug(f"Found feature for table {feature_table_class.__name__}, match_id: {match_id}")
            return feature_instance
        except Exception as e:
            logger.error(f"Error fetching feature from {feature_table_class.__name__} for match_id {match_id}: {e}", exc_info=True)
            raise

    async def get_all_features_from_table(self, feature_table_class: Type[T]) -> List[T] | Exception:
        """
        Retrieves all feature model instances from the specified table.

        Args:
            feature_table_class: The SQLModel table class (e.g., HeroFeaturesTable).

        Returns:
            A list of SQLModel instances of type T. Returns empty list if table is empty or on error.
        """
        try:
            list_instances: List[T] = await self._get_all_data_by_class(feature_table_class)

            if not list_instances:
                logger.warning(f"No features found in table {feature_table_class.__name__}")
                return []

            logger.debug(f"Retrieved {len(list_instances)} features from table {feature_table_class.__name__}")
            return list_instances
        except Exception as e:
            logger.error(f"Error fetching all features from {feature_table_class.__name__}: {e}", exc_info=True)
            raise