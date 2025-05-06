from feature_engineering import TeamFeatureProcessor, PlayerHeroFeaturesProcessor, create_hero_features, preprocess_live_match_data
from data_repository.features_repository import FeaturesRepository
import pandas as pd
from utils.set_logging import get_logger

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
        
    async def create_and_store_features(self, match_dataframe: pd.DataFrame) -> bool:
        if match_dataframe.empty:
            logger.warning(f'Empty dataframe found')
            return False
        
        processed_dataframe = preprocess_live_match_data(match_dataframe)
        if processed_dataframe.empty:
            logger.warning(f'dataframe is empty after preprocessing')
            return False
        
        # to consider? wrap in coroutine?
        try:
            hero_features: pd.DataFrame = create_hero_features(processed_dataframe)
            team_features: pd.DataFrame = await self.team_feature_processor.create_team_features(processed_dataframe)
            player_hero_features: pd.DataFrame = await self.player_hero_processor.create_player_hero_features(processed_dataframe)
        except Exception as e:
            logger.error(f"Error creating features {e}", exc_info=True)
            return False
        
        # to consider? wrap in coroutine too?
        try:
            await self.storage.store_features(hero_features)
            await self.storage.store_features(team_features)
            await self.storage.store_features(player_hero_features)
        except Exception as e:
            logger.error(f"Error storing features {e}", exc_info=True)
            return False
        
        return True