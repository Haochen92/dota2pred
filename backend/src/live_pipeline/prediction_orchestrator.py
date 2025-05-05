import numpy as np
from utils.set_logging import get_logger
from .match_prediction_service import MatchPredictionService
from inference import FeaturePreparationService
from .redis_service import RedisService
from constants.redis_constants import PREDICTION_GROUP, STREAM_PENDING_PREDICTION

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = 'consumer_one'

class PredictionOrchestrator:
    """
    Orchestrates the prediction step by processing events from the
    pending prediction stream (STREAM_PENDING_PREDICTION).
    """
    def __init__(
        self,
        redis_service: RedisService,
        feature_preparation_service: FeaturePreparationService,
        match_prediction_service: MatchPredictionService,
        consumer_name: str = DEFAULT_CONSUMER_NAME
    ):
        self.redis = redis_service
        self.feature_preparation_service = feature_preparation_service
        self.match_prediction_service = match_prediction_service
        self.consumer_name = consumer_name
        logger.info(f"Initialized PredictionOrchestrator for consumer '{self.consumer_name}' on stream '{STREAM_PENDING_PREDICTION}'")


    async def run_prediction_cycle(self) -> int:
        """
        Processes one batch of matches pending prediction.

        Returns:
            The number of events successfully processed in this cycle.
        """
        logger.info(f"PredictionOrchestrator: Fetching from {STREAM_PENDING_PREDICTION} for consumer {self.consumer_name}...")

        events = await self.redis.fetch_matches_pending_prediction(self.consumer_name)

        if not events:
            logger.debug(f"PredictionOrchestrator: No new events in {STREAM_PENDING_PREDICTION}")
            return 0
        else:
            logger.info(f"PredictionOrchestrator: Found {len(events)} new events from {STREAM_PENDING_PREDICTION}")

        events_processed = 0
        for event_id, data in events.items():
            match_id = int(data.get('match_id'))
            try:
                # Prepare features using the preparation service
                input_array: np.ndarray | None = await self.feature_preparation_service.get_transformed_features_from_id(match_id)

                if input_array is None or input_array.size == 0:
                    raise ValueError(f"PredictionOrchestrator: Feature preparation failed or returned empty features for match {match_id}. Event ID: {event_id}")

                prediction_result = await self.match_prediction_service.predict_and_store(match_id)

                if prediction_result is None:
                    raise ValueError(f"No prediction result, inference failed... at prediction Orchestrator")

                await self.redis.advance_match_to_pending_completion(match_id, event_id) 
                events_processed += 1
                logger.debug(f"PredictionOrchestrator: Successfully processed prediction for match {match_id}, Event ID: {event_id}")

            except Exception as e:
                logger.error(f"PredictionOrchestrator: Unhandled error processing prediction for match_id: {match_id}, event_id: {event_id}", exc_info=True)
                await self.redis.record_failure_and_ack(
                    original_stream=STREAM_PENDING_PREDICTION,
                    group=PREDICTION_GROUP,
                    event_id=event_id,
                    event_data=data,
                    error=e
                )
                continue

        logger.info(f"PredictionOrchestrator: Finished cycle, processed {events_processed} prediction events.")
        return events_processed