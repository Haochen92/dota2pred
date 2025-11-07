import pandas as pd
import numpy as np
from typing import Optional

from sqlalchemy.exc import SQLAlchemyError

from dota_oracle_pipeline.feature_transformation.aggregate_features import create_final_features
from dota_oracle_common.models.inference.schema import ModelMetaDataAPIResponse

from dota_oracle_common.utils.set_logging import get_logger

from dota_oracle_common.models.redis.schema import PredictionPayload


logger = get_logger(__name__)

# Feature keys:
HERO_KEY = "hero"
TEAM_KEY = "team"
PLAYER_HERO_KEY = "player_hero"


class FeaturePreparationService:
    def __init__(self, model_metadata: ModelMetaDataAPIResponse):
        # Now it depends on the data it actually needs.
        self.model_feature_names = list(model_metadata.version_metadata.feature_columns)
        if not self.model_feature_names:
            raise ValueError("feature_columns in metadata is empty")

    async def prepare_features_for_inference(self, raw_features: PredictionPayload) -> Optional[np.ndarray]:
        """
        Fetches raw features, processes, encodes, merges, and returns a NumPy array.
        """
        try:

            team_features = raw_features.team_features
            hero_features = raw_features.hero_features
            player_hero_features = raw_features.player_hero_features

            if not team_features or not hero_features or not player_hero_features:
                logger.warning("One or more feature sets are missing in raw features")
                return None

            final_features = create_final_features(
                hero_features_list=[hero_features],
                team_features_list=[team_features],
                player_hero_features_list=[player_hero_features],
            )

            final_features_df = pd.DataFrame([feature.model_dump() for feature in final_features])

            if final_features_df is None or final_features_df.empty:
                logger.warning("Empty dataframe or None after creating final features")
                return None

            # Select and order columns as expected by the model metadata
            required_columns = self.model_feature_names
            missing = [col for col in required_columns if col not in final_features_df.columns]
            if missing:
                raise ValueError(
                    f"Missing required feature columns for inference: {missing}. "
                    f"Available columns: {list(final_features_df.columns)}"
                )

            ordered_df = final_features_df[required_columns]

            # Convert final DataFrame to NumPy array in the exact model order
            numpy_array: np.ndarray = ordered_df.to_numpy()
            logger.info(
                f"Successfully prepared features, final shape: {numpy_array.shape} with columns: {required_columns}"
            )
            return numpy_array

        except SQLAlchemyError as e:
            logger.error(f"Database error during feature preparation for match: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during feature preparation for match : {e}", exc_info=True)
            raise
