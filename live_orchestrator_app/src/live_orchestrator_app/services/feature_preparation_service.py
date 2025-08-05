import pandas as pd
import numpy as np
from typing import Optional, Tuple, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.models.features import TeamFeaturesTable, HeroFeaturesTable, PlayerHeroFeatureTable
from dota_oracle_common.repositories.heroes_repository import HeroesRepository

from dota_oracle_pipeline.feature_transformation import FeatureEncoder
from live_orchestrator_app.services.model_inference_service import ModelInferenceService

from dota_oracle_common.utils.set_logging import get_logger


logger = get_logger(__name__)

# Feature keys:
HERO_KEY = "hero"
TEAM_KEY = "team"
PLAYER_HERO_KEY = "player_hero"


class FeaturePreparationService:
    def __init__(self, model_inference_service: ModelInferenceService):
        self.model_inference_service = model_inference_service
        self.model_feature_names = self._extract_feature_columns()

    def _extract_feature_columns(self) -> List[str]:
        model_metadata = self.model_inference_service.model_metadata
        feature_columns = model_metadata.version_metadata.feature_columns

        if not feature_columns:
            raise ValueError(f"feature_columns returned invalid value of {feature_columns}")

        return list(feature_columns)

    async def prepare_features_for_inference(self, match_id: int, db_session: AsyncSession) -> Optional[np.ndarray]:
        """
        Fetches raw features, processes, encodes, merges, and returns a NumPy array.
        """
        logger.info(f"Starting feature preparation for match {match_id}")
        try:
            # init repositories
            match_repository = MatchRepository(session=db_session)
            heroes_repository = HeroesRepository(session=db_session)

            # Get Features from database
            res = await self._get_features_from_db(match_id, match_repository)

            if not res:
                logger.warning(f"Incomplete features for match: {match_id}")
                return None

            team_features, hero_features, player_hero_features = res

            # Convert features to dataframe
            team_df = pd.DataFrame([team_features.model_dump(exclude={"match"})])
            hero_df = pd.DataFrame([hero_features.model_dump(exclude={"match"})])
            player_hero_df = pd.DataFrame([player_hero_features.model_dump(exclude={"match"})])

            # Encode hero_df
            encoded_hero_df = await self._encode_hero_feature(heroes_repository, hero_df)

            if encoded_hero_df is None or encoded_hero_df.empty:
                logger.warning(f"Empty dataframe or None after encoding hero_df for match {match_id}")
                return None

            # merge all features into a single dataframe
            final_features_df = self._merge_and_filter_dataframe(
                hero_features=encoded_hero_df, team_features=team_df, player_hero_features=player_hero_df
            )

            if final_features_df is None or final_features_df.empty:
                logger.warning(f"Feature merging/filtering resulted in None or empty DataFrame for match {match_id}")
                return None

            # Convert final DataFrame to NumPy array
            numpy_array: np.ndarray = final_features_df.to_numpy()
            logger.info(f"Successfully prepared features for match {match_id}, final shape: {numpy_array.shape}")
            return numpy_array

        except SQLAlchemyError as e:
            logger.error(f"Database error during feature preparation for match {match_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during feature preparation for match {match_id}: {e}", exc_info=True)
            raise

    async def _get_features_from_db(
        self, match_id: int, match_repository: MatchRepository
    ) -> Optional[Tuple[TeamFeaturesTable, HeroFeaturesTable, PlayerHeroFeatureTable]]:

        # get features from repository
        res = await match_repository.get_match_details(
            input_id_list=[match_id],
            relationship_fields=["team_features", "player_hero_features", "hero_features"],
            limit=1,
        )
        if not res:
            logger.warning(f"No Match data created for match: {match_id}")
            return None

        match_instance = res[0]

        # Extract out feature instances from match
        team_features = match_instance.team_features
        hero_features = match_instance.hero_features
        player_hero_features = match_instance.player_hero_features

        if not team_features or not hero_features or not player_hero_features:
            logger.warning(
                f"features incomplete for match {match_id}: "
                f"team_features: {team_features}, "
                f"hero_features: {hero_features}, "
                f"player_hero_features: {player_hero_features}"
            )
            return None

        return team_features, hero_features, player_hero_features

    async def _encode_hero_feature(
        self, heroes_repository: HeroesRepository, hero_dataframe: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        # Get hero Map
        hero_map = await heroes_repository.get_hero_id_map()
        if not hero_map:
            logger.warning("Missing hero_map. Unable to proceed with data encoding.")
            return None

        encoded_hero_df: Optional[pd.DataFrame] = FeatureEncoder.encode_hero_features(hero_dataframe, hero_map)

        if encoded_hero_df is None or encoded_hero_df.empty:
            return None

        return encoded_hero_df

    def _merge_and_filter_dataframe(
        self, hero_features: pd.DataFrame, team_features: pd.DataFrame, player_hero_features: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """Merges feature DataFrames and filters columns based on model requirements."""
        try:
            dataframes = [hero_features, team_features, player_hero_features]
            if any("match_id" not in df.columns for df in dataframes):
                logger.error("match_id missing from one or more feature dataframes before merge.")
                return None

            combined_features = hero_features.merge(player_hero_features, on="match_id", how="inner")
            combined_features = combined_features.merge(team_features, on="match_id", how="inner")

            if combined_features.empty:
                logger.warning("Feature merge resulted in empty DataFrame (inner join condition not met?).")
                return None

            missing_cols = [col for col in self.model_feature_names if col not in combined_features.columns]
            if missing_cols:
                logger.error(f"Final combined features missing required columns: {missing_cols}")
                return None

            final_dataframe = combined_features[self.model_feature_names]
            return final_dataframe

        except Exception as e:
            logger.error(f"Error during _merge_and_filter_dataframe: {e}", exc_info=True)
            raise
