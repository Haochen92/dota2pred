import pandas as pd
import redis
from typing import Dict, Any
from ml_pipeline.preprocessing import preprocess_live_df
from ml_pipeline.features import create_and_store_hero_features, TeamFeatureProcessor, PlayerHeroFeatures
from ml_pipeline.features.feature_transformation import get_transformed_features
from .live_match_storage import LiveMatchStorage

class LiveFeatureProcessor:
    def __init__(self, redis_client: redis.Redis, storage: LiveMatchStorage):
        self.redis = redis_client
        self.storage = LiveMatchStorage    
    
    async def _create_and_store_features(self, match_details: Dict[str, Any]):
        input_df = pd.DataFrame([match_details])
        df = preprocess_live_df(input_df)
        await create_and_store_hero_features(df, self.engine)
        teamfeature_obj = TeamFeatureProcessor(self.redis, self.engine)
        await teamfeature_obj.create_and_store_team_features(df)
        playerherofeature_obg = PlayerHeroFeatures(self.redis, self.engine) 
        await playerherofeature_obg.create_and_store_player_hero_features(df)