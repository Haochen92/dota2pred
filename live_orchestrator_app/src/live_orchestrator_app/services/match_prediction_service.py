from dota_oracle_common.repositories.prediction_repository import PredictionRepository
from live_orchestrator_app.services.model_inference_service import ModelInferenceService
from live_orchestrator_app.services.feature_preparation_service import FeaturePreparationService
import numpy as np
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse
from dota_oracle_common.models.inference import MatchPredictionTable
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class MatchPredictionService:
    def __init__(
        self,
        features_preparation_service: FeaturePreparationService,
        model_inference_service: ModelInferenceService,
    ):
        self.feature_preparation_service = features_preparation_service
        self.model_inference_service = model_inference_service

    async def predict_and_store(
        self, db_session: AsyncSession, match_id: int, input_array_for_inference: np.ndarray
    ) -> None:
        try:
            prediction_instance: ModelPredictionAPIResponse = await self.model_inference_service.get_prediction(
                input_array_for_inference
            )
            prediction_list = prediction_instance.prediction
            prediction = prediction_list[0]
            logger.info(f"Successfully fetched prediction for match: {match_id}, value: {prediction}")
        except Exception as e:
            logger.error(f"Error when making prediction for {match_id}: {e}", exc_info=True)
            raise e

        try:
            metadata = self.model_inference_service.model_metadata
            prediction_table = MatchPredictionTable(
                match_id=match_id,
                prediction=bool(prediction),
                predictor_name=metadata.name,
                predictor_version=metadata.version,
                prediction_date=get_current_utc_iso_timestamp(),
            )

            prediction_repository = PredictionRepository(session=db_session)
            await prediction_repository.store_match_prediction(match_prediction=prediction_table)
        except Exception as e:
            logger.error(f"Failed to store predictions for match {match_id}: {e}", exc_info=True)
            raise e
