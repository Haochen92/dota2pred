import time
import pandas as pd
import numpy as np
import redis
from typing import Dict, Any
from utils.set_logging import get_logger
from .redis_constants import PREDICTION_GROUP, ONGOING_STREAM, MATCH_STATUS, PREDICTED_STREAM

# import pydantic models
from pydantic_models.inference import ModelPrediction, ModelMetaData

# import Repository types
from .match_pipeline_orchestrator import (
    FeaturesRepository, 
    PredictionRepository, 
    HeroesRepository, 
    HistoryRepository)

# import schema tables
from data_repository.schemas import PlayerHeroFeatureTable, HeroFeaturesTable, TeamFeaturesTable

# import services
from inference.feature_preparation import FeaturePreparationService, ModelInferenceService
from feature_engineering import (
    PlayerHeroFeaturesProcessor, 
    TeamFeatureProcessor,
    create_hero_features,
    preprocess_live_match_data
)

logger = get_logger(__name__)

class OngoingMatchProcessor:
    async def __init__(
        self, 
        redis_client: redis.Redis, 
        feature_storage: FeaturesRepository,
        prediction_storage: PredictionRepository,
        hero_storage: HeroesRepository,
        history_storage: HistoryRepository
    ):
        self.redis = redis_client
        self.feature_storage = feature_storage
        self.prediction_storage = prediction_storage
        self.hero_storage = hero_storage
        self.history_storage = history_storage
        
        await self._instantiate_services()
        
    async def _instantiate_services(self) -> None:
        self.model_inference_service = ModelInferenceService()
        
        # get model_metadata
        try:
            self.model_metadata: ModelMetaData = await self.model_inference_service.get_model_metadata()
        except Exception as e:
            logger.error(f"Error fetching metadata: {e}")
        self.feature_preparation_service = FeaturePreparationService(
            self.hero_storage,
            self.model_metadata.feature_columns
        )
        # instantiate feature processors
        self.player_hero_feature_processor = PlayerHeroFeaturesProcessor(self.history_storage)
        self.team_feature_processor = TeamFeatureProcessor(self.history_storage)
        
    async def process_ongoing_matches(self, curr_matches: Dict[int, Dict[str, Any]]) -> int:
        """
        Process ongoing matches for predictions.

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
        
        # Can wrap in coroutine 
        for stream_name, stream_events in events:
            for event_id, data in stream_events:
                try:
                    match_id = int(data['match_id']) # convert raw str to int
                    
                    match_details = curr_matches.get(match_id, {})
                    
                    if not match_details:
                        logger.warning(f"match_details for match_id {match_id} is empty")
                        return pd.DataFrame([{}])
                    
                    input_dataframe = pd.DataFrame([match_details])
                
                    # Feature Engineering
                    prepared_features = await self._create_and_store_features(input_dataframe)
                    
                    # Match Prediction
                    prediction = await self._infer_and_store_prediction(match_id, prepared_features)
                    
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
                except Exception as e:
                    logger.error(f"Error encountered processing event: {event_id} with data: {data}")
                    continue
        
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
    
    async def _create_and_store_features(self, match_dataframe: pd.DataFrame) -> np.ndarray:
        preprocessed_df = preprocess_live_match_data(match_dataframe)
        
        # create features
        hero_features = create_hero_features(preprocessed_df)
        team_features = await self.team_feature_processor.create_team_features(preprocessed_df)
        player_hero_features = await self.player_hero_feature_processor.create_player_hero_features(preprocessed_df)
        
        # store features
        await self.feature_storage.store_features(hero_features, HeroFeaturesTable)
        await self.feature_storage.store_features(team_features, TeamFeaturesTable)
        await self.feature_storage.store_features(player_hero_features, PlayerHeroFeatureTable)
        
        # transform and prepare features for inference
        prepared_features = await self.feature_preparation_service.get_transformed_features_from_df(
            hero_features_df=hero_features,
            team_features_df=team_features,
            player_hero_features_df=player_hero_features
        )
        
        return prepared_features
        
    async def _infer_and_store_prediction(self, match_id: int, input_features: np.ndarray) -> int:
         model_res: ModelPrediction = await self.model_inference_service.get_prediction(input_features)
         prediction = model_res.prediction[0] # first and only value from array
         
         # store prediction
         await self.prediction_storage.store_match_prediction(
             match_id=match_id,
             prediction=prediction,
             predictor_name=self.model_metadata.name,
             predictor_version=self.model_metadata.version
         )
         
         return prediction