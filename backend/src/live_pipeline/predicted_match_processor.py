import pandas as pd
from typing import Dict, Any, Set, Optional, List
from data_pipeline.fetching.fetch_match_details import get_match_details
from ml_pipeline.features import create_and_store_hero_features, TeamFeatureProcessor, PlayerHeroFeatures
from data_pipeline.storage.store_live_match import insert_live_match_outcome
from pydantic_models.match import Match


class PredictedMatchProcessor:
    async def _process_predicted_matches(self, curr_matches: Dict[int, Dict[str, Any]]) -> int:
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
                match_id = int(data['match_id'])
                
                # If the match is no longer in the current live matches,
                # it means it's completed
                if match_id not in curr_match_ids:
                    completed_match_details = await get_match_details(match_id)
                    match_outcome =  completed_match_details.radiant_win
                    if match_outcome is not None:
                        await insert_live_match_outcome(
                            engine=self.engine,
                            match_id=match_id,
                            outcome=match_outcome  
                        )
                        await self._update_histories(completed_match_details)
                                              
                        cleanup_pipe = self.redis.pipeline()
                        # For now we're just cleaning up
                        cleanup_pipe.delete(f'{MATCH_STATUS}:{match_id}')
                        
                        # Acknowledge processing of this event
                        cleanup_pipe.xack(PREDICTED_STREAM, COMPLETION_GROUP, event_id)
                        cleanup_pipe.execute()
                        
                        events_processed += 1
        logger.info(f"{events_processed} predicted matches have completed.")
        return events_processed

    async def _update_histories(self, match_details: Match) -> None:
        try:
            match_dict = match_details.model_dump()
            match_df = pd.DataFrame(match_dict)
            teamfeature_obj = TeamFeatureProcessor(self.redis, self.engine)
            await teamfeature_obj.update_all_team_histories(match_df)
            playerherofeature_obg = PlayerHeroFeatures(self.redis, self.engine) 
            await playerherofeature_obg.update_all_player_hero_histories(match_df,match_details.radiant_win)
        except Exception as e:
            logger.error("Error updating match histories for match {match_details.match_id}: {e}")