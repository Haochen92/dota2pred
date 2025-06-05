from dota_oracle.feature_engineering import TeamFeatureProcessor, PlayerHeroFeaturesProcessor, create_hero_features, preprocess_live_match_data
from dota_oracle.data_repository.features_repository import FeaturesRepository
from dota_oracle.models.match import MatchTable
from dota_oracle.models.features import HeroFeaturesTable, TeamFeaturesTable, PlayerHeroFeatureTable
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.utils.async_utils import run_updates_as_group
from typing import Coroutine, List, Any

logger = get_logger(__name__)
                        
class FeatureEngineeringService:
    
    def __init__(
        self, 
        team_feature_processor: TeamFeatureProcessor,
        player_hero_processor: PlayerHeroFeaturesProcessor,
        features_repository: FeaturesRepository,
    ):
        self.team_feature_processor = team_feature_processor
        self.player_hero_processor = player_hero_processor
        self.storage = features_repository
        
    async def create_and_store_features(self, match_instance: MatchTable) -> None:
        if not match_instance:
            logger.warning("no match_instances for data creation")
            return None
        
        processed_match_instance = preprocess_live_match_data(match_instance)
        if not processed_match_instance:
            raise ValueError("Dataframe is empty after processing")
        
        try:
            hero_features: List[HeroFeaturesTable] = create_hero_features([processed_match_instance])
            team_features: List[TeamFeaturesTable] = await self.team_feature_processor.create_team_features([processed_match_instance]) 
            player_hero_features: List[PlayerHeroFeatureTable] = await self.player_hero_processor.create_player_hero_features([processed_match_instance]) 
        except Exception as e:
            logger.error(f"Error creating features {e}", exc_info=True)
            raise e
        
        if not hero_features or not team_features or not player_hero_features:
            raise ValueError("Features are not created successfully")
        
        storage_task: list[Coroutine[Any, Any, None]] = [
            self.storage.store_features(feature_instances=hero_features, table_class=HeroFeaturesTable),
            self.storage.store_features(feature_instances=team_features, table_class=TeamFeaturesTable), 
            self.storage.store_features(feature_instances=player_hero_features, table_class=PlayerHeroFeatureTable) 
        ]
        
        try:
            await run_updates_as_group(storage_task)
        except Exception as e:
            logger.error(f"Error storing features {e}", exc_info=True)
            raise e
        