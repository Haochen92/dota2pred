from sqlalchemy.ext.asyncio import AsyncSession

from typing import Optional

from dota_oracle_common.models.api.schema import PredictionDetailsResponse, PredictionDetailsRequest
from dota_oracle_common.models.features import (
    AllFeaturesDTO,
)
from dota_oracle_common.models.inference import MatchPrediction

from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.repositories.prediction_repository import PredictionRepository

from dota_oracle_pipeline.feature_transformation.aggregate_features import create_final_features

from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)


class PredictionDetailsService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_prediction_details_for_match(self, request: PredictionDetailsRequest) -> PredictionDetailsResponse:
        """
        Fetches detailed prediction information for a given match ID.

        Args:
            match_id (int): The ID of the match to fetch details for.
        """
        match_id = request.match_id

        logger.info(f"Fetching prediction details for match ID: {match_id}")

        features = await self._fetch_and_aggregate_features(match_id)
        prediction = await self._fetch_prediction_details(match_id)

        # Create and return the response
        return PredictionDetailsResponse(features=features, prediction_details=prediction)

    async def _fetch_and_aggregate_features(self, match_id: int) -> Optional[AllFeaturesDTO]:
        features_repository = FeaturesRepository(self.db_session)

        try:
            team_features = await features_repository.get_team_features([match_id])
            hero_features = await features_repository.get_hero_features([match_id])
            player_hero_features = await features_repository.get_player_hero_features([match_id])

            if not team_features or not hero_features or not player_hero_features:
                logger.warning(f"Features not found for match ID {match_id}")
                return None

            aggregated_features = create_final_features(
                team_features_list=team_features,
                hero_features_list=hero_features,
                player_hero_features_list=player_hero_features,
            )

            return aggregated_features[0]
        except Exception as e:
            raise Exception(f"Error fetching or aggregating features: {e}")

    async def _fetch_prediction_details(self, match_id: int) -> Optional[MatchPrediction]:
        prediction_repository = PredictionRepository(self.db_session)

        try:
            prediction = await prediction_repository.get_all_predictions_match_id(match_id)

            if not prediction or len(prediction) == 0:
                logger.warning(f"Prediction not found for match ID {match_id}")
                return None
            return prediction[0]
        except Exception as e:
            raise Exception(f"Error fetching prediction from database: {e}")
