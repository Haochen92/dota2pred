import numpy as np
from utils.set_logging import get_logger
from .match_prediction_service import MatchPredictionService
from inference import FeaturePreparationService
from .redis_service import RedisService
from constants.redis_constants import PREDICTION_GROUP, STREAM_PENDING_PREDICTION
from utils.async_utils import get_outcome_concurrently
from typing import Coroutine, Any, Dict
from pydantic_models.redis_models import StreamMatchEventData, FailureRecord
from utils.time_utils import get_current_utc_iso_timestamp

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

        events: Dict[str, StreamMatchEventData] = await self.redis.fetch_matches_pending_prediction(self.consumer_name)

        if not events:
            logger.debug(f"PredictionOrchestrator: No new events in {STREAM_PENDING_PREDICTION}")
            return 0
        else:
            logger.info(f"PredictionOrchestrator: Found {len(events)} new events from {STREAM_PENDING_PREDICTION}")

        event_task_group: Dict[str, Coroutine[Any, Any, bool]] = {}
        
        for event_id, data in events.items():
            event_task_group[event_id] = self._run_single_prediction_cycle(event_id, data)

        res = await get_outcome_concurrently(event_task_group)
            
        successful_events = 0
        failed_events = 0
        
        for event_id, outcome in res.items():
            if outcome and not isinstance(outcome, Exception):
                successful_events += 1
            else:
                failed_events += 1

        logger.info(f"PredictionOrchestrator: Finished cycle, with {successful_events} successful events, and {failed_events} failures")
        return successful_events
    
    
    async def _run_single_prediction_cycle(self, event_id:str, data: StreamMatchEventData) -> bool:
        try:
            input_array: np.ndarray | None = await self.feature_preparation_service.get_transformed_features_from_id(data.match_id)

            if input_array is None or input_array.size == 0: # Correct way of checking empty or uninitalised numpy array
                raise ValueError(f"PredictionOrchestrator: Feature preparation failed or returned empty features for match {data.match_id}. Event ID: {event_id}")

            prediction_result = await self.match_prediction_service.predict_and_store(data.match_id)

            if isinstance(prediction_result, Exception):
                raise prediction_result
            await self.redis.advance_match_to_pending_completion(data.match_id, event_id)
            return True
        except Exception as e:
            logger.error(f"PredictionOrchestrator: Unhandled error processing prediction for match_id: {data.match_id}, event_id: {event_id}", exc_info=True)
            failure_record = FailureRecord(
                original_group=PREDICTION_GROUP,
                original_event_id=event_id,
                original_data=data,
                original_stream=STREAM_PENDING_PREDICTION,
                error_message=e,
                failure_timestamp=get_current_utc_iso_timestamp()
            )
            await self.redis.record_failure_and_ack(failure_record)
            return False