import pandas as pd
import redis
from typing import Dict, Any, Set, Optional, List
from .redis_constants import MATCH_STATUS
from .match_pipeline_orchestrator import (
    COMPLETION_GROUP, PREDICTED_STREAM,
    HistoryRepository, MatchRepository
)
from data_extraction.fetch_match_details import fetch_match_details, MatchesAPIResponse
from utils.set_logging import get_logger

logger = get_logger(__name__)

class PredictedMatchProcessor:
    def __init__(
        self, 
        redis_client: redis.Redis,
        history_repository: HistoryRepository,
        match_respository: MatchRepository
    ):
        self.redis = redis_client
        self.history_repository = history_repository
        self.match_repository = match_respository
    
    async def process_predicted_matches(self, curr_matches: Dict[int, Dict[str, Any]]) -> int:
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
                try:
                    match_id = int(data['match_id'])
                    
                    # If the match is no longer in the current live matches,
                    # it means it's completed
                    if match_id not in curr_match_ids:
                        completed_match_details: MatchesAPIResponse = await fetch_match_details(match_id)
                        match_outcome = completed_match_details.radiant_win
                        match_outcome =  completed_match_details.radiant_win
                        if match_outcome is not None:
                            await self.match_repository.insert_match_outcome(match_id, match_outcome)
                            await self._update_histores(completed_match_details)
                                                
                            cleanup_pipe = self.redis.pipeline()
                            cleanup_pipe.delete(f'{MATCH_STATUS}:{match_id}')
                            
                            # Acknowledge processing of this event
                            cleanup_pipe.xack(PREDICTED_STREAM, COMPLETION_GROUP, event_id)
                            cleanup_pipe.execute()
                            
                            events_processed += 1
                except Exception as e:
                    logger.error(f"Error processing predicted match {event_id}, {e}", exc_info=True)
                    continue
                
        logger.info(f"{events_processed} predicted matches have completed.")
        return events_processed

    async def _update_histories(self, match_details: MatchesAPIResponse) -> None:
        try:
            # team histories
            await self.history_repository.add_team_match_outcome(
                team_name=match_details.radiant_name,
                match_id=match_details.match_id,
                win=match_details.radiant_win,
                match_start_time=match_details.start_time
            )
            await self.history_repository.add_team_match_outcome(
                team_name=match_details.dire_name,
                match_id=match_details.match_id,
                win= not match_details.radiant_win,
                match_start_time=match_details.start_time
            )
            
            # team match_up histories
            await self.history_repository.add_team_match_up_outcome(
                team_one=match_details.radiant_name,
                team_two=match_details.dire_name,
                match_id=match_details.match_id,
                win=match_details.radiant_win,
                match_start_time=match_details.start_time
            )
            
            # update player histories
            for player_data in match_details.players:
                player_slot:int = player_data.player_slot
                account_id = player_data.account_id
                hero_id=player_data.hero_id
                
                if player_slot in range(0, 5):
                    win = match_details.radiant_win
                else:
                    win = not match_details.radiant_win
                    
                await self.history_repository.add_player_hero_match_outcome(
                    account_id=account_id,
                    hero_id=hero_id,
                    match_id=match_details.match_id,
                    win=win,
                    match_start_time=match_details.start_time
                )
        except Exception as e:
            logger.error(f"Error updating match histories for match {match_details.match_id}: {e}", exc_info=True)