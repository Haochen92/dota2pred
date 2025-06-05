from typing import Dict, Coroutine, Any, List, Set, Tuple
from dota_oracle.utils.set_logging import get_logger
from .feature_engineering_service import FeatureEngineeringService
from ..redis_service import RedisService
from dota_oracle.constants.redis_constants import STREAM_NEW_MATCHES, FEATURE_ENGINEER_GROUP
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.models.match import MatchTable
from dota_oracle.utils.async_utils import run_updates_as_group, get_outcome_concurrently
from dota_oracle.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle.models.redis.schema import StreamMatchEventData, FailureRecord
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

logger = get_logger(__name__)

DEFAULT_CONSUMER_NAME = 'consumer_one'

class FeatureEngineeringOrchestrator:
    """
    Orchestrates the feature engineering step by processing events from
    the new matches stream (STREAM_NEW_MATCHES).
    
    This orchestrator:
    1. Fetches pending feature engineering events from Redis
    2. Retrieves corresponding match data from the database
    3. Coordinates feature engineering and Redis state updates
    4. Handles failures and maintains data consistency
    """
    
    def __init__(
        self,
        redis_service: RedisService,
        feature_engineering_service: FeatureEngineeringService,
        db_engine: AsyncEngine,
        consumer_name: str = DEFAULT_CONSUMER_NAME
    ):
        self.redis_service = redis_service
        self.feature_engineering_service = feature_engineering_service
        self.consumer_name = consumer_name
        self.db_engine = db_engine
        
        logger.info(
            f"Initialized FeatureEngineeringOrchestrator: "
            f"consumer='{self.consumer_name}', stream='{STREAM_NEW_MATCHES}'"
        )

    async def run_feature_engineering_cycle(self) -> int:
        """
        Executes a complete feature engineering cycle.
        
        Process:
        1. Fetch pending events from Redis stream
        2. Validate and prepare event data
        3. Retrieve match details from database
        4. Execute feature engineering concurrently
        5. Update Redis with results
        
        Returns:
            Number of events successfully processed
        """
        logger.info(f"Starting feature engineering cycle for consumer '{self.consumer_name}'")
        
        try:
            # Step 1: Fetch pending events from Redis
            pending_events = await self._fetch_pending_events_from_redis()
            if not pending_events:
                logger.debug("No pending events found - cycle complete")
                return 0
            
            # Step 2: Validate event data and extract match IDs
            validated_events, invalid_events = self._validate_and_categorize_events(pending_events)
            await self._handle_invalid_events(invalid_events)
            
            if not validated_events:
                logger.warning("No valid events found after validation")
                return 0
            
            # Step 3: Fetch match details from database
            match_data_lookup = await self._fetch_match_details_for_events(validated_events)
            
            # Step 4: Execute feature engineering for all valid matches
            processing_results = await self._execute_feature_engineering_batch(
                validated_events, match_data_lookup
            )
            
            # Step 5: Log and return results
            successful_count = sum(1 for success in processing_results.values() if success)
            failed_count = len(processing_results) - successful_count
            
            logger.info(
                f"Feature engineering cycle complete: "
                f"successful={successful_count}, failed={failed_count}, total={len(pending_events)}"
            )
            
            return successful_count
            
        except Exception as e:
            logger.error(f"Critical failure in feature engineering cycle: {e}", exc_info=True)
            return 0

    async def _fetch_pending_events_from_redis(self) -> Dict[str, StreamMatchEventData]:
        """
        Fetches pending feature engineering events from the Redis stream.
        
        Returns:
            Dictionary mapping event_id -> event_data
        """
        logger.debug(f"Fetching events from stream '{STREAM_NEW_MATCHES}'")
        
        try:
            events = await self.redis_service.fetch_new_matches_for_feature_eng(self.consumer_name)
            
            if events:
                logger.info(f"Retrieved {len(events)} pending events from Redis stream")
            else:
                logger.debug("No pending events in Redis stream")
                
            return events
            
        except Exception as e:
            logger.error(f"Failed to fetch events from Redis stream: {e}", exc_info=True)
            return {}

    def _validate_and_categorize_events(
        self, 
        events: Dict[str, StreamMatchEventData]
    ) -> Tuple[Dict[str, StreamMatchEventData], Dict[str, StreamMatchEventData]]:
        """
        Validates event data and separates valid from invalid events.
        
        Args:
            events: Raw events from Redis stream
            
        Returns:
            Tuple of (valid_events, invalid_events)
        """
        valid_events = {}
        invalid_events = {}
        
        for event_id, event_data in events.items():
            if self._is_event_data_valid(event_data):
                valid_events[event_id] = event_data
            else:
                invalid_events[event_id] = event_data
                logger.warning(f"Invalid event data for event_id='{event_id}': {event_data}")
        
        logger.info(f"Event validation: valid={len(valid_events)}, invalid={len(invalid_events)}")
        return valid_events, invalid_events

    def _is_event_data_valid(self, event_data: StreamMatchEventData) -> bool:
        """
        Validates individual event data.
        
        Args:
            event_data: Event data to validate
            
        Returns:
            True if event data is valid, False otherwise
        """
        if not event_data:
            return False
            
        if not hasattr(event_data, 'match_id') or not event_data.match_id:
            return False
            
        if not isinstance(event_data.match_id, int) or event_data.match_id <= 0:
            return False
            
        return True

    async def _handle_invalid_events(self, invalid_events: Dict[str, StreamMatchEventData]) -> None:
        """
        Handles events with invalid data by recording failures.
        
        Args:
            invalid_events: Dictionary of invalid events to handle
        """
        if not invalid_events:
            return
            
        logger.warning(f"Handling {len(invalid_events)} invalid events")
        
        for event_id, event_data in invalid_events.items():
            await self._record_event_failure(
                event_data=event_data,
                event_id=event_id,
                error=ValueError("Invalid event data structure"),
                context="event_validation"
            )

    async def _fetch_match_details_for_events(
        self, 
        events: Dict[str, StreamMatchEventData]
    ) -> Dict[int, MatchTable]:
        """
        Fetches match details from database for all events.
        
        Args:
            events: Valid events requiring match data
            
        Returns:
            Dictionary mapping match_id -> match_details
        """
        match_ids = [event_data.match_id for event_data in events.values()]
        unique_match_ids = list(set(match_ids))  # Remove duplicates
        
        logger.info(f"Fetching match details for {len(unique_match_ids)} unique matches")
        
        try:
            async with AsyncSession(self.db_engine) as session:
                match_repository = MatchRepository(session=session)
                
                match_details_list = await match_repository.get_match_details(
                    input_id_list=unique_match_ids
                )
                
                if not match_details_list:
                    logger.warning("No match details found in database")
                    return {}
                
                # Create lookup dictionary
                match_data_lookup = {
                    match.match_id: match for match in match_details_list
                }
                
                found_count = len(match_data_lookup)
                missing_count = len(unique_match_ids) - found_count
                
                logger.info(
                    f"Match data retrieval: found={found_count}, missing={missing_count}"
                )
                
                if missing_count > 0:
                    missing_ids = set(unique_match_ids) - set(match_data_lookup.keys())
                    logger.warning(f"Missing match details for IDs: {missing_ids}")
                
                return match_data_lookup
                
        except Exception as e:
            logger.error(f"Database error while fetching match details: {e}", exc_info=True)
            return {}

    async def _execute_feature_engineering_batch(
        self,
        valid_events: Dict[str, StreamMatchEventData],
        match_data_lookup: Dict[int, MatchTable]
    ) -> Dict[str, bool]:
        """
        Executes feature engineering for all valid events concurrently.
        
        Args:
            valid_events: Events to process
            match_data_lookup: Match data indexed by match_id
            
        Returns:
            Dictionary mapping event_id -> success_status
        """
        logger.info(f"Executing feature engineering for {len(valid_events)} events")
        
        # Prepare concurrent tasks
        concurrent_tasks = {}
        skipped_events = {}
        
        for event_id, event_data in valid_events.items():
            match_id = event_data.match_id
            match_details = match_data_lookup.get(match_id)
            
            if not match_details:
                logger.warning(f"Skipping event '{event_id}' - no match data for match_id={match_id}")
                skipped_events[event_id] = False
                continue
            
            concurrent_tasks[event_id] = self._process_single_event(
                event_id=event_id,
                event_data=event_data,
                match_details=match_details
            )
        
        if not concurrent_tasks:
            logger.warning("No events can be processed - all lack match data")
            return skipped_events
        
        logger.info(f"Executing {len(concurrent_tasks)} concurrent feature engineering tasks")
        
        # Execute all tasks concurrently
        task_results = await get_outcome_concurrently(concurrent_tasks)
        
        # Combine results
        all_results = {**task_results, **skipped_events}
        return all_results

    async def _process_single_event(
        self,
        event_id: str,
        event_data: StreamMatchEventData,
        match_details: MatchTable
    ) -> bool:
        """
        Processes a single event through feature engineering and Redis update.
        
        Args:
            event_id: Unique event identifier
            event_data: Event data from Redis stream
            match_details: Match data from database
            
        Returns:
            True if processing succeeded, False otherwise
        """
        match_id = event_data.match_id
        
        try:
            logger.debug(f"Processing event '{event_id}' for match_id={match_id}")
            
            # Create task group for concurrent execution
            task_group = [
                self.feature_engineering_service.create_and_store_features(match_details),
                self.redis_service.advance_match_to_pending_prediction(match_id, event_id)
            ]
            
            # Execute both operations
            await run_updates_as_group(task_group)
            
            logger.debug(f"Successfully processed event '{event_id}' for match_id={match_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to process event '{event_id}' for match_id={match_id}: {e}",
                exc_info=True
            )
            
            await self._record_event_failure(
                event_data=event_data,
                event_id=event_id,
                error=e,
                context="feature_engineering_execution"
            )
            
            return False

    async def _record_event_failure(
        self,
        event_data: StreamMatchEventData,
        event_id: str,
        error: Exception,
        context: str
    ) -> None:
        """
        Records a failure for an individual event.
        
        Args:
            event_data: Original event data
            event_id: Event identifier
            error: Exception that caused the failure
            context: Context where the failure occurred
        """
        try:
            failure_record = FailureRecord(
                original_event_id=event_id,
                original_stream=STREAM_NEW_MATCHES,
                original_group=FEATURE_ENGINEER_GROUP,
                original_data=event_data,
                error_type=type(error).__name__,
                error_message=f"[{context}] {str(error)}",
                failure_timestamp=get_current_utc_iso_timestamp()
            )
            
            await self.redis_service.record_failure_and_ack(failure_record)
            
            logger.info(f"Recorded failure for event '{event_id}' in context '{context}'")
            
        except Exception as e:
            logger.error(
                f"Failed to record failure for event '{event_id}': {e}",
                exc_info=True
            )