from feature_engineering import TeamFeatureProcessor, PlayerHeroFeaturesProcessor, create_hero_features, preprocess_live_match_data
from data_repository.features_repository import FeaturesRepository
import pandas as pd
from utils.set_logging import get_logger
from utils.async_utils import run_updates_as_group
from typing import Coroutine, List, Any

logger = get_logger(__name__)
                        
class FeatureEngineeringService:
    def __init__(
        self, 
        team_feature_processor = TeamFeatureProcessor,
        player_hero_processor = PlayerHeroFeaturesProcessor,
        features_repository = FeaturesRepository,
    ):
        self.team_feature_processor = team_feature_processor
        self.player_hero_processor = player_hero_processor
        self.storage = features_repository
        
    async def create_and_store_features(self, match_dataframe: pd.DataFrame) -> None:
        if match_dataframe.empty:
            raise ValueError("input Dataframe is empty")
        
        processed_dataframe = preprocess_live_match_data(match_dataframe)
        if processed_dataframe.empty:
            raise ValueError("Dataframe is empty after processing")
        
        try:
            hero_features: pd.DataFrame = create_hero_features(processed_dataframe)
            team_features: pd.DataFrame = await self.team_feature_processor.create_team_features(processed_dataframe)
            player_hero_features: pd.DataFrame = await self.player_hero_processor.create_player_hero_features(processed_dataframe)
        except Exception as e:
            logger.error(f"Error creating features {e}", exc_info=True)
            raise e
        
        if hero_features.empty or team_features.empty or player_hero_features.empty:
            raise ValueError("features dataframes are created but empty")
        
        storage_task: List[Coroutine[Any, Any, None]] = [
            self.storage.store_features(hero_features),
            self.storage.store_features(team_features),
            self.storage.store_features(player_hero_features)
        ]
        
        try:
            await run_updates_as_group(storage_task)
        except Exception as e:
            logger.error(f"Error storing features {e}", exc_info=True)
            raise e
        