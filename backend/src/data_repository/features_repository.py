import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from .base_repository import BaseRepository, SQLModelTable, T
from utils.set_logging import get_logger
from typing import Optional, List, Dict, Any, Type
from .schemas.features import HeroFeaturesTable, PlayerHeroFeatureTable, TeamFeaturesTable

logger = get_logger(__name__)

class FeaturesRepository(BaseRepository):
    """
    Repository class for handling database operations related to
    match features (Hero, Team, Player-Hero).
    Uses asynchronous SQLAlchemy Core and targets PostgreSQL.
    """
    def __init__(self, engine: AsyncEngine):
        super().__init__(engine=engine)

    async def _batch_upsert(
        self,
        table_class: Type[SQLModelTable],
        records: List[Dict[str, Any]], 
        session: AsyncSession
    ) -> int:

        if not records:
            logger.info(f"No records provided for batch upsert into {table_class.__name__}")
            return 0

        sql_table = table_class.__table__
        table_name = table_class.__name__

        try:
            # Use column names for comparison/lookup
            primary_key = 'match_id'
            update_cols = {c.name for c in sql_table.columns if c.name != primary_key}

            update_dict = {
                col_name: getattr(insert(sql_table).excluded, col_name)
                for col_name in update_cols
            }

            stmt = insert(sql_table).values(records).on_conflict_do_update(
                index_elements=[primary_key], # Pass the original list of names here
                set_=update_dict
            )

            await session.execute(stmt) 
            logger.info(f"Batch upsert into {table_name} completed for {len(records)} input records.")
            
            return len(records)
        except Exception as e:
            logger.error(f"Error during batch upsert into {table_name}: {str(e)}", exc_info=True)
            raise e


    async def store_features(
        self,
        feature_dataframe: pd.DataFrame,
        table_class: Type[SQLModelTable]
    ) -> None:
        """
        Stores features from a DataFrame into the specified table using batch upsert.
        """
        if feature_dataframe.empty:
            logger.info(f"Received empty DataFrame for storing features in {table_class.__name__}. Skipping.")
            return

        feature_records = feature_dataframe.to_dict(orient='records')
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                await self._batch_upsert(
                    session=session,
                    table_class=table_class, 
                    records=feature_records,
                )


    async def get_feature_by_id(self, match_id: int, feature_table_class: Type[SQLModelTable])-> pd.DataFrame:
        """
        Retrieves a single feature record by its primary key (assumed to be 'match_id' here).
        """
        try:
            feature_instance: Optional[SQLModelTable] = await self._get_instance_by_id(feature_table_class, match_id)

            if not feature_instance:
                logger.warning(f"No feature found for table {feature_table_class.__name__}, match_id: {match_id}")
                return pd.DataFrame()

            return pd.DataFrame([feature_instance.model_dump()])
        except Exception as e:
            logger.error(f"Error fetching feature from {feature_table_class.__name__} for match_id {match_id}: {e}", exc_info=True)
            raise e

    async def get_all_features_from_table(self, feature_table_class: Type[SQLModelTable]) -> pd.DataFrame:
        """
        Retrieves all feature records from the specified table.
        """
        try:
            list_instances: List[SQLModelTable] = await self._get_all_data_by_class(feature_table_class)

            if not list_instances:
                logger.warning(f"No features found in table {feature_table_class.__name__}")
                return pd.DataFrame()

            features_df = pd.DataFrame([instance.model_dump() for instance in list_instances])

            return features_df
        except Exception as e:
            logger.error(f"Error fetching all features from {feature_table_class.__name__}: {e}", exc_info=True)
            raise e