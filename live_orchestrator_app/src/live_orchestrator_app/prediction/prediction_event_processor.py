from dota_oracle_common.utils.set_logging import get_logger
from live_orchestrator_app.services.feature_preparation_service import FeaturePreparationService
from live_orchestrator_app.services.match_prediction_service import MatchPredictionService
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from dota_oracle_common.models.redis.schema import (
    ConsumedEvent,
    PredictionPayload,
    CompletionPayload,
)

logger = get_logger(__name__)


class PredictionEventProcessor:
    """
    Event processor for handling prediction events. Prepares features,
    makes a prediction, stores it, and returns the result.
    """

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        feature_preparation_service: FeaturePreparationService,
        match_prediction_service: MatchPredictionService,
    ):
        self.feature_preparation_service = feature_preparation_service
        self.match_prediction_service = match_prediction_service
        self.db_session_factory = db_session_factory

    async def process_event(self, event: ConsumedEvent[PredictionPayload]) -> CompletionPayload:
        """
        Processes a single prediction work item.
        This method handles one unit of work.

        Args:
            work_item: PredictionWorkItem containing event data
        """
        match_id = event.match_id
        raw_features = event.payload

        try:
            logger.debug(f"Processing prediction for match_id={match_id}")
            async with self.db_session_factory() as session:
                async with session.begin():
                    # Prepare features for inference
                    input_array = await self.feature_preparation_service.prepare_features_for_inference(raw_features)
                    logger.info(f"Finished feature preparation for match {match_id}")

                    if input_array is None or input_array.size == 0:
                        raise ValueError(f"Feature preparation failed or returned empty features for match {match_id}")

                    # Make prediction and store
                    predicted_outcome = await self.match_prediction_service.predict_and_store(
                        db_session=session, match_id=match_id, input_array_for_inference=input_array
                    )

                    logger.debug(f"Successfully processed prediction for match_id={match_id}")

        except Exception as e:
            logger.error(f"Failed to process prediction for match_id={match_id}: {e}", exc_info=True)
            raise e

        return CompletionPayload(match_id=match_id, radiant_win=bool(predicted_outcome))
