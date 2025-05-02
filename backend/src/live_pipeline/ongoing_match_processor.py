import time
import pandas as pd
import redis
from typing import Dict, Any
from feature_engineering.features_preprocessing import preprocess_live_df
from ml_pipeline.features import create_and_store_hero_features, TeamFeatureProcessor, PlayerHeroFeatures
from ml_pipeline.features.feature_transformation import get_transformed_features
from ml_pipeline.inference.model_inference import PredictionService
from utils.set_logging import get_logger
from .redis_constants import PREDICTION_GROUP, ONGOING_STREAM, MATCH_STATUS, PREDICTED_STREAM
from .live_match_storage import LiveMatchStorage

logger = get_logger(__name__)

class OngoingMatchProcessor:
    def __init__(self, redis_client: redis.Redis, storage: LiveMatchStorage):
        self.redis = redis_client
        self.storage = storage
        
    async def process_ongoing_matches(self, curr_matches: Dict[int, Dict[str, Any]]) -> int:
        """Process ongoing matches for predictions.
        
        Args:
            curr_matches: Dictionary of match_id to match details
        """
        logger.info("processing ongoing matches...")
        
        events = self.retrieve_ongoing_events()
        if not events:
            logger.info("no ongoing events found...")
            return 0
        
        logger.info(f'found {len(events)} ongoing events...')
        
        events_processed = 0
        pipe = self.redis.pipeline()
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        for stream_name, stream_events in events:
            for event_id, data in stream_events:
                
                match_id = int(data['match_id'])
                
                match_details = curr_matches.get(match_id, {})
             
                # Feature Engineering
                await self._create_and_store_features(match_details)
                
                # Match Prediction
                await self._get_match_prediction(match_id)
                
                # Append prediction and Update match status
                pipe.hset(f'{MATCH_STATUS}:{match_id}','status','predicted')
                
                # Add to predicted matches stream
                pipe.xadd(
                    PREDICTED_STREAM, 
                    {'match_id': match_id, 'timestamp': timestamp}
                )
                
                # Acknowledge processing of this event
                pipe.xack(ONGOING_STREAM, PREDICTION_GROUP, event_id)
                
                events_processed += 1
        
        pipe.execute()
        logger.info(f"processed {events_processed} ongoing matches")
        return events_processed
    
    def retrieve_ongoing_events(self) -> Any:
        # Read new events from the ongoing matches stream
        events = self.redis.xreadgroup(
            PREDICTION_GROUP, 
            'consumer1', 
            {ONGOING_STREAM: '>'}, 
            count=100  # Limit batch size
        )
        
        return events
    
    async def _create_and_store_features(self, match_details: Dict[str, Any]):
        input_df = pd.DataFrame([match_details])
        df = preprocess_live_df(input_df)
        await create_and_store_hero_features(df, self.engine)
        teamfeature_obj = TeamFeatureProcessor(self.redis, self.engine)
        await teamfeature_obj.create_and_store_team_features(df)
        playerherofeature_obg = PlayerHeroFeatures(self.redis, self.engine) 
        await playerherofeature_obg.create_and_store_player_hero_features(df)
        
    async def _get_match_prediction(self, match_id: int) -> int:
        df_features = await get_transformed_features(engine=self.engine, match_id=match_id)
        prediction_service = PredictionService(self.engine)
        prediction = await prediction_service.predict_and_store(df_features)
        return prediction