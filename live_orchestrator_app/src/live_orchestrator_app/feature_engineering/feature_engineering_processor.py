from dota_oracle_common.utils.set_logging import get_logger
from live_orchestrator_app.services.feature_engineering_service import FeatureEngineeringService
from dota_oracle_common.models.pipeline import FeatureEngineeringWorkItem
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = get_logger(__name__)

class FeatureEngineeringEventProcessor:
    """Event processor for handling single feature engineering work items."""
    
    def __init__(
        self,
        feature_engineering_service: FeatureEngineeringService,
        db_engine: AsyncEngine
    ):
        self.feature_engineering_service = feature_engineering_service
        self.engine = db_engine
    
    async def process_event(self, work_item: FeatureEngineeringWorkItem) -> None:
        """
        Processes a single feature engineering work item.
        Creates its own transaction for this unit of work.
        
        Args:
            work_item: FeatureEngineeringWorkItem containing event and match data
        """
        match_id = work_item.event_data.match_id
        event_id = work_item.event_id
        
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    logger.debug(f"Processing feature engineering for event '{event_id}', match_id={match_id}")
                    
                    # Create and store features with session
                    await self.feature_engineering_service.create_and_store_features(work_item.match_details, session)
                    
                    logger.debug(f"Successfully processed feature engineering for event '{event_id}', match_id={match_id}")
                    
                except Exception as e:
                    logger.error(
                        f"Failed to process feature engineering for event '{event_id}', match_id={match_id}: {e}",
                        exc_info=True
                    )
                    raise e