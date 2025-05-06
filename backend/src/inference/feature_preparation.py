import pandas as pd
import numpy as np
import asyncio
from typing import Optional, List
from feature_transformation.encoding import encode_hero_features
from data_repository.features_repository import FeaturesRepository
from data_repository.heroes_repository import HeroesRepository
from utils.set_logging import get_logger
from inference.model_inference import ModelInferenceService

logger = get_logger(__name__)

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
        """Fetches features by ID, prepares them, and returns a NumPy array."""
        try:
            # Fetch concurrently 
            tasks = [
                self.feature_repo.get_hero_features(match_id),
                self.feature_repo.get_team_features(match_id),
                self.feature_repo.get_player_hero_features(match_id),
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check results (handles None and exceptions)
            hero_features, team_features, player_hero_features = results

            # Handle exceptions during fetch
            for i, res in enumerate(results):
                 if isinstance(res, Exception):
                      logger.error(f"Failed to fetch feature set {i} for match {match_id}: {res}")
                      return None

            # Check for None results (valid fetch but no data)
            if hero_features is None or team_features is None or player_hero_features is None:
                logger.warning(f"One or more feature sets not found in DB for match_id: {match_id}")
                return None
            
            # Check for empty dataframes (valid fetch, data exists, but is empty)
            if hero_features.empty or team_features.empty or player_hero_features.empty:
                logger.warning(f"One or more feature sets are empty for match_id: {match_id}")
                return None # Or handle differently if empty frames are valid input for merge/encode

        except Exception as e:
            # Catch any other unexpected error during setup/gather
            logger.error(f"Unexpected error fetching features for match {match_id}: {e}", exc_info=True)
            return None # Or re-raise

        try:
             hero_features_encoded = await encode_hero_features(hero_features, self.heros_repository)
             if hero_features_encoded is None or hero_features_encoded.empty:
                  logger.error(f"Hero feature encoding failed or returned empty for match {match_id}")
                  return None


             final_features_df = self._merge_and_filter_dataframe(
                 hero_features=hero_features_encoded, 
                 team_features=team_features,
                 player_hero_features=player_hero_features
             )

             if final_features_df is None: # Check if merge/filter failed
                 return None

             return final_features_df.to_numpy()

        except Exception as e:
             logger.error(f"Failed to prepare features after fetching for match {match_id}: {e}", exc_info=True)
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
    ) -> Optional[pd.DataFrame]: # Return Optional DataFrame
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
