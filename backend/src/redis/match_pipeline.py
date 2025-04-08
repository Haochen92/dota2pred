import redis
import time
from typing import Dict, Any, Set, Optional
from src.utils.set_logging import get_logger
from src.pipeline.datafetching.fetch_live_leagues import retrieve_live_league_games
from src.pipeline.datafetching.fetch_match_details import get_match_details

logger = get_logger(__name__)

# Constants
MATCH_SET = 'live_match_ids'
ONGOING_STREAM = 'ongoing_matches'
PREDICTED_STREAM = 'predicted_matches'
PREDICTION_GROUP = 'prediction_group'
COMPLETION_GROUP = 'completion_group'

class MatchPipeline:
    """Pipeline for processing live matches, making predictions, and tracking outcomes."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._ensure_consumer_groups()
        
    def _ensure_consumer_groups(self) -> None:
        self._create_group(ONGOING_STREAM, PREDICTION_GROUP)
        self._create_group(PREDICTED_STREAM, COMPLETION_GROUP)
        
    def _create_group(self, stream:str, group: str) -> None:
        try:
            self.redis.xgroup_create(stream, group, id='0', mkstream=True)
            logger.info(f"Created consumer group {group} for stream {stream}")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                logger.info(f"Consumer group {group} already exists")
            else:
                logger.error(f"Error creating group {group}: {str(e)}")
                raise 
    
    async def poll_live_matches(self) -> int:
        # Add statics of total operations performed. 
        try:
            # get current live matches
            curr_matches = self._get_current_matches()
            if not curr_matches:
                logger.info("No live matches found")
                return 0
            
            # update live matches set and identify new matches
            new_match_ids = self._update_live_matches_set(curr_matches)
            
            # process new matches
            count_new_matches = self._process_new_matches(new_match_ids, curr_matches)
            
            # process ongoing matches
            count_predicted_matches = self._process_ongoing_matches(curr_matches)
            
            # process predicted matches for completion
            count_completed_matches = self._process_predicted_matches(curr_matches)
            
            logger.info(
                f"""Pipeline stats: 
                new_matches: {count_new_matches}
                predicted_matches {count_predicted_matches} 
                completed_matches: {count_completed_matches}
                """
            )
                       
            return len(new_match_ids)
        
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {str(e)}")
            return 0
        except Exception as e:
            logger.error(f"Unexpected error in poll_live_matches: {str(e)}")
            return 0
        
    async def _get_current_matches(self) -> Dict[str, Dict[str, Any]]:
        
        res = retrieve_live_league_games()
        if not res:
            return {}
        
        return {item['match_id']: item for item in res}

    async def _update_live_matches_set(self, curr_matches: Dict[str, Dict[str, Any]]) -> Set[str]:
        
        curr_match_ids = list(curr_matches.keys())
        tmp_key = f'{MATCH_SET}:temp'
        
        # Delete last polling from tmp_key
        self.redis.delete(tmp_key)
        
        if curr_match_ids:
            self.redis.sadd(tmp_key, *curr_match_ids)
            # find new matches
            new_matches_ids = self.redis.sdiff(tmp_key, MATCH_SET)
            # Replace main set with temp set
            self.redis.rename(tmp_key, MATCH_SET)
            logger.info(f"Found {len(new_matches_ids)} new matches")
            return new_matches_ids
        else:
            return set()
        
    async def _process_new_matches(self, 
                             new_match_ids: Set[str], 
                             curr_matches: Dict[str, Dict[str, Any]]
    ) -> int:
        if not new_match_ids:
            return 0
        
        matches_processed = 0
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        pipe = self.redis.pipeline()
        
        for match_id in new_match_ids:
            match_details = curr_matches.get(match_id, {})
            if match_details:
                # Store matches with status
                pipe.hset(
                    f'match_details:{match_id}',
                    mapping={**match_details, 'status':'ongoing'}
                )
                pipe.xadd(
                    ONGOING_STREAM, 
                    {'match_id': str(match_id), 'timestamp': timestamp}
                )
                matches_processed += 1
        pipe.execute()
        
        return matches_processed
        
    async def _process_ongoing_matches(self, curr_matches: Dict[str, Dict[str, Any]]) -> int:
        """Process ongoing matches for predictions.
        
        Args:
            curr_matches: Dictionary of match_id to match details
        """
        # Read new events from the ongoing matches stream
        events = self.redis.xreadgroup(
            PREDICTION_GROUP, 
            'consumer1', 
            {ONGOING_STREAM: '>'}, 
            count=100  # Limit batch size
        )
        
        if not events:
            return 0
        
        events_processed = 0
        pipe = self.redis.pipeline()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        for stream_name, stream_events in events:
            for event_id, data in stream_events:
                match_id = data['match_id']
                match_details = curr_matches.get(match_id, {})
                game_duration = match_details.get('game_duration', 0)
                
                if game_duration > 0:
                    # Here you would call your prediction logic
                    
                    # For now we're just logging
                    logger.info(f"Making predictions for match {match_id}")
                    
                    # Update match status
                    pipe.hset(f'match_details:{match_id}', 'status', 'predicted')
                    
                    # Add to predicted matches stream
                    pipe.xadd(
                        PREDICTED_STREAM, 
                        {'match_id': str(match_id), 'timestamp': timestamp}
                    )
                    
                    # Acknowledge processing of this event
                    pipe.xack(ONGOING_STREAM, PREDICTION_GROUP, event_id)
                    
                    events_processed += 1
        
        pipe.execute()
        return events_processed
    
    async def _process_predicted_matches(self, curr_matches: Dict[str, Dict[str, Any]]) -> int:
        """Process predicted matches for completion.
        
        Args:
            curr_matches: Dictionary of match_id to match details
        """
        # Read new events from the predicted matches stream
        events = self.redis.xreadgroup(
            COMPLETION_GROUP, 
            'consumer1', 
            {PREDICTED_STREAM: '>'}, 
            count=100  # Limit batch size
        )
        
        if not events:
            return 0
        
        events_processed = 0

        curr_match_ids = set(curr_matches.keys())
        
        for stream_name, stream_events in events:
            for event_id, data in stream_events:
                match_id = data['match_id']
                
                # If the match is no longer in the current live matches,
                # it means it's completed
                if match_id not in curr_match_ids:
                    outcome = await self._get_match_outcome(match_id) 
                    if outcome is not None:
                        # Append match outcome to hset
                        pipe = self.redis.pipeline()
                        pipe.hset(f'match_details:{match_id}', mapping={
                            'status':'completed', 
                            'radiant_win': outcome
                        })
                        # Here you would store the outcome in your database
                         # Get the match details
                        pipe.hgetall(f'match_details:{match_id}')
                        
                        # Execute to get the updated match details
                        results = pipe.execute()
                        match_details = results[1] 
                        
                        db_operation = await self._store_to_database(match_details)
                        if not db_operation:
                            continue
                        
                        cleanup_pipe = self.redis.pipeline()
                        # For now we're just cleaning up
                        cleanup_pipe.delete(f'match_details:{match_id}')
                        
                        # Acknowledge processing of this event
                        cleanup_pipe.xack(PREDICTED_STREAM, COMPLETION_GROUP, event_id)
                        cleanup_pipe.execute()
                        
                        events_processed += 1
        
        return events_processed

    async def _get_match_outcome(self, match_id: str) -> Optional[bool]:
        res = await get_match_details(match_id)
        if not res:
            return None
        
        return res.get('radiant_win', None)
    
    async def _store_to_database(self, match_details: Dict) -> bool:
        '''Store result to database'''
        try:
            # Store to database
            return True
        except Exception as e:
            return False