from dota_oracle_common.utils.set_logging import get_logger
from live_orchestrator_app.services.feature_preparation_service import FeaturePreparationService
from live_orchestrator_app.services.match_prediction_service import MatchPredictionService
from dota_oracle_common.models.pipeline import PredictionWorkItem
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

logger = get_logger(__name__)


class PredictionEventProcessor:
    """Event processor for handling single prediction work items."""

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        feature_preparation_service: FeaturePreparationService,
        match_prediction_service: MatchPredictionService,
    ):
        self.feature_preparation_service = feature_preparation_service
        self.match_prediction_service = match_prediction_service
        self.db_session_factory = db_session_factory

    async def process_event(self, work_item: PredictionWorkItem) -> None:
        """
        Processes a single prediction work item.
        This method handles one unit of work.

        Args:
            work_item: PredictionWorkItem containing event data
        """
        match_id = work_item.match_id
        event_id = work_item.event_id

        try:
            logger.debug(f"Processing prediction for event '{event_id}', match_id={match_id}")
            async with self.db_session_factory() as session:
                async with session.begin():
                    # Prepare features for inference
                    input_array = await self.feature_preparation_service.prepare_features_for_inference(
                        match_id, session
                    )

                    if input_array is None or input_array.size == 0:
                        raise ValueError(f"Feature preparation failed or returned empty features for match {match_id}")

                    # Make prediction and store
                    await self.match_prediction_service.predict_and_store(
                        db_session=session, match_id=match_id, input_array_for_inference=input_array
                    )

                    logger.debug(f"Successfully processed prediction for event '{event_id}', match_id={match_id}")
        except Exception as e:
            logger.error(
                f"Failed to process prediction for event '{event_id}', match_id={match_id}: {e}", exc_info=True
            )
            raise e
