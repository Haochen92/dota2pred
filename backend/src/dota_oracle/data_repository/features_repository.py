from sqlalchemy.ext.asyncio import AsyncSession
from .base_repository import BaseRepository, T
from dota_oracle.utils.set_logging import get_logger
from typing import Optional, List, Type

logger = get_logger(__name__)

class FeaturesRepository(BaseRepository):
    
    def __init__(self, session:AsyncSession):
        super().__init__(session)
        self.session = session
    """
    Repository class for handling database operations related to
    match features (Hero, Team, Player-Hero).
    Uses asynchronous SQLAlchemy Core and targets PostgreSQL.
    Returns SQLModel instances or lists thereof.
    """

    async def store_features(
        self,
        feature_instances: List[T],
        table_class: Type[T],
    ) -> None:
        """
        Stores features from a DataFrame into the specified table using batch upsert.
        Converts DataFrame rows to dictionaries for storage.
        """
        if not feature_instances:
            logger.warning(f"Received empty list for storing features in {table_class.__name__}. Skipping.")
            return
        try:
            await self._upsert_data(
                model_class=table_class,
                instances=feature_instances,
            )
        except Exception as e:
            raise e
    
    async def get_features(
        self,
        *, 
        table_class: Type[T],
        match_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,  
    ) -> List[T]:
        """
        Returns a list of features based on the input match_ids.

        Args:
            match_ids: Optional list of primary key match ids. If none provided, fetch all the data
            feature_table_class: The SQLModel table class (e.g., HeroFeaturesTable).

        Returns:
            A list of instances, empty list if not found
        """
        try:
            feature_instance_list = await self._get_data(
                model_class=table_class,
                id_filters=match_ids,
                limit=limit
            )
            
            if not feature_instance_list:
                debug_message = (
                    f"No results found for table {table_class.__name__}, "
                    f"inputs: {match_ids}"
                )
                logger.debug(debug_message)
                return []
            
            logger.info(f"Found {len(feature_instance_list)} results")
            return feature_instance_list
        except Exception as e:
            raise e

    