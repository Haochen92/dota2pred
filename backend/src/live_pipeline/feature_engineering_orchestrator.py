import pandas as pd
from typing import Dict
from utils.set_logging import get_logger
from .feature_engineering_service import FeatureEngineeringService
from .redis_service import RedisService
from constants.redis_constants import STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP
from data_repository.match_repository import MatchRepository

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = 'consumer_one'

class FeatureEngineeringOrchestrator:
    """
    Orchestrates the feature engineering step by processing events from
    the new matches stream (STREAM_NEW_MATCHES).
    """
    def __init__(
        self,
        redis_service: RedisService,
        feature_engineering_service: FeatureEngineeringService,
        match_repository: MatchRepository,
        consumer_name: str = DEFAULT_CONSUMER_NAME
    ):
        self.redis = redis_service
        self.feature_engineering_service = feature_engineering_service
        self.consumer_name = consumer_name
        self.storage = match_repository
        logger.info(f"Initialized FeatureEngineeringOrchestrator for consumer '{self.consumer_name}' on stream '{STREAM_NEW_MATCHES}'")

    async def run_feature_engineering_cycle(self) -> int:
        """
        Fetches batch and process new matches for feature engineering 
        
        Returns:
            The number of events successfully processed in this cycle.
        """
        logger.info(f"FeatureEngineeringOrchestrator: Fetching from {STREAM_NEW_MATCHES} for consumer {self.consumer_name}...")

        events = await self.redis.fetch_new_matches_for_feature_eng(self.consumer_name)

        if not events:
            logger.debug(f"FeatureEngineeringOrchestrator: No new events in {STREAM_NEW_MATCHES}")
            return 0
        else:
            logger.info(f"FeatureEngineeringOrchestrator: Found {len(events)} new events from {STREAM_NEW_MATCHES}")

        events_processed = 0
        
        match_details_dict = await self._fetch_matches_from_db(events)
        if not match_details_dict:
            logger.warning(f"no match details found in the database")
            return 0
        
        for event_id, data in events.items():
            match_id = data['match_id']
            try:
                match_details = match_details_dict.get(match_id)

                if not match_details:
                    raise ValueError(f"FeatureEngineeringOrchestrator: Match details missing in curr_matches for completed/ended match? Match ID: {match_id}, Event ID: {event_id}")

                # Create DataFrame for the service
                input_dataframe = pd.DataFrame([match_details])

                # Call the feature engineering service
                success = await self.feature_engineering_service.create_and_store_features(input_dataframe)

                if not success:
                    raise ValueError(f"FeatureEngineeringOrchestrator: Feature engineering service failed for match: {match_id}, Event ID: {event_id}")

                await self.redis.advance_match_to_pending_prediction(match_id, event_id)
                events_processed += 1
                logger.debug(f"FeatureEngineeringOrchestrator: Successfully processed match {match_id}, Event ID: {event_id}")

            except Exception as e:
                logger.error(f"FeatureEngineeringOrchestrator: Unhandled error processing match_id: {match_id}, event_id: {event_id}", exc_info=True)
                await self.redis.record_failure_and_ack(
                    original_stream=STREAM_NEW_MATCHES,
                    group=FEATURE_ENGINEER_GROUP,
                    event_id=event_id,
                    event_data=data,
                    error=e
                )
                continue

        logger.info(f"FeatureEngineeringOrchestrator: Finished cycle, processed {events_processed} events.")
        return events_processed
    
    
    async def _fetch_matches_from_db(self, events: Dict[str, dict]) -> Dict[str, Dict[str, any]]:
        list_matches_instances = [data['match_id'] for data in events.values()]
        batch_matches = await self.storage.get_match_details_batch(list_matches_instances)
        
        if not batch_matches:
            return {}
        match_dict = {str(match.match_id) : match.model_dump() for match in batch_matches}
        return match_dict
        