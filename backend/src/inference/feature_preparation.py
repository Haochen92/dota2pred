import pandas as pd
import numpy as np
import asyncio
from sqlmodel import SQLModel
from typing import Optional, Union, List, Dict, Coroutine, Any
from feature_transformation.encoding import encode_hero_features
from data_repository.schemas.features import HeroFeaturesTable, TeamFeaturesTable, PlayerHeroFeatureTable
from data_repository.features_repository import FeaturesRepository
from data_repository.heroes_repository import HeroesRepository
from utils.set_logging import get_logger
from inference.model_inference import ModelInferenceService
from utils.async_utils import get_outcome_as_group

logger = get_logger(__name__)

# Feature keys:
HERO_KEY = 'hero'
TEAM_KEY = 'team'
PLAYER_HERO_KEY = 'player_hero'

FetchResult = Union[Optional[SQLModel], Exception]

class FeaturePreparationService:
    def __init__(
        self,
        features_repository: FeaturesRepository,
        heroes_repository: HeroesRepository,
        model_inference_service: ModelInferenceService
    ):
        self.feature_repo = features_repository
        self.model_inference_service = model_inference_service
        self.heros_repository = heroes_repository
        self.model_feature_names: List[str] = model_inference_service.model_metadata.feature_columns
        if not self.model_feature_names:
            raise ValueError(f"Empty column feature names when initialising service")
        
    async def get_transformed_features_from_id(self, match_id: int) -> Optional[np.ndarray]:
        """
        Fetches raw features, processes, encodes, merges, and returns a NumPy array.
        """
        logger.info(f"Starting feature preparation for match {match_id}")

        tasks_group: Dict[str, Coroutine[Any, Any, SQLModel]] = {
            HERO_KEY: self.feature_repo.get_feature_by_id(match_id, HeroFeaturesTable),
            TEAM_KEY: self.feature_repo.get_feature_by_id(match_id, TeamFeaturesTable),
            PLAYER_HERO_KEY: self.feature_repo.get_feature_by_id(match_id, PlayerHeroFeatureTable)
        }
        

        try:
            outcome_dict: Dict[str, SQLModel] = await get_outcome_as_group(tasks_group)
            logger.info(f"Successfully retrieved all raw feature sets for match {match_id}. Proceeding with processing.")

            hero_df = pd.DataFrame([outcome_dict[HERO_KEY].model_dump()])
            team_df = pd.DataFrame([outcome_dict[TEAM_KEY].model_dump()])
            player_hero_df = pd.DataFrame([outcome_dict[PLAYER_HERO_KEY].model_dump()])

            encoded_hero_df = await encode_hero_features(hero_df, self.heros_repository)
            
            final_features_df = self._merge_and_filter_dataframe(
                hero_features=encoded_hero_df,
                team_features=team_df,
                player_hero_features=player_hero_df
            )

            if final_features_df is None or final_features_df.empty:
                logger.warning(f"Feature merging/filtering resulted in None or empty DataFrame for match {match_id}")
                return None

            # Convert final DataFrame to NumPy array
            numpy_array = final_features_df.to_numpy()
            logger.info(f"Successfully prepared features for match {match_id}, final shape: {numpy_array.shape}")
            return numpy_array

        except KeyError as e:
            logger.error(f"Internal processing error (missing key {e}?) for match {match_id}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Failed during feature processing/merging stage for match {match_id}: {e}", exc_info=True)
            return None

    async def get_transformed_features_from_df(
        self,
        hero_features_df: pd.DataFrame,
        team_features_df: pd.DataFrame,
        player_hero_features_df: pd.DataFrame
    ) -> Optional[np.ndarray]:
        """Prepares features from input DFs and returns a NumPy array."""
        try:
            if hero_features_df is None or hero_features_df.empty or \
               team_features_df is None or team_features_df.empty or \
               player_hero_features_df is None or player_hero_features_df.empty:
                 logger.error("One or more input feature DataFrames are missing or empty.")
                 # Raise error as caller provided invalid input
                 raise ValueError("Missing or empty input features DataFrame(s)")

            hero_features_encoded = await encode_hero_features(hero_features_df, self.heros_repository)
            if hero_features_encoded is None or hero_features_encoded.empty:
                 logger.error("Hero feature encoding failed or returned empty")
                 raise ValueError("Hero feature encoding failed")


            final_features_df = self._merge_and_filter_dataframe(
                hero_features=hero_features_encoded, 
                team_features=team_features_df,
                player_hero_features=player_hero_features_df
            )

            if final_features_df is None: 
                 raise ValueError("Feature merging or filtering failed")

            return final_features_df.to_numpy()

        except ValueError as ve: 
            logger.warning(f"ValueError during feature preparation from DFs: {ve}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error preparing features from DFs: {e}", exc_info=True)
            raise RuntimeError("Unexpected error during feature preparation") from e


    def _merge_and_filter_dataframe(
        self,
        hero_features: pd.DataFrame,
        team_features: pd.DataFrame,
        player_hero_features: pd.DataFrame
    ) -> Optional[pd.DataFrame]: 
        """Merges feature DataFrames and filters columns based on model requirements."""
        try:
            # Check required merge column exists
            if 'match_id' not in hero_features.columns or \
               'match_id' not in team_features.columns or \
               'match_id' not in player_hero_features.columns:
                logger.error("match_id missing from one or more feature dataframes before merge.")
                return None

            combined_features = hero_features.merge(player_hero_features, on='match_id', how='inner')
            combined_features = combined_features.merge(team_features, on='match_id', how='inner')

            if combined_features.empty:
                logger.warning("Feature merge resulted in empty DataFrame (inner join condition not met?).")
                return None

            missing_cols = [
                col for col in self.model_feature_names
                if col not in combined_features.columns
            ]
            if missing_cols:
                logger.error(f"Final combined features missing required columns: {missing_cols}")
                return None

            final_dataframe = combined_features[self.model_feature_names]
            return final_dataframe

        except Exception as e:
             logger.error(f"Error during _merge_and_filter_dataframe: {e}", exc_info=True)
             return None 
