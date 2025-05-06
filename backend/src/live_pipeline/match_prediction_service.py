from data_repository.prediction_repository import PredictionRepository
from inference import ModelInferenceService, FeaturePreparationService
import numpy as np
from utils.set_logging import get_logger
from pydantic_models.inference import ModelPrediction

logger = get_logger(__name__)

class MatchPredictionService:
    def __init__(
        self, 
        features_preparation_service: FeaturePreparationService, 
        model_inference_service: ModelInferenceService,
        prediction_repository: PredictionRepository
    ):
        self.feature_preparation_service = features_preparation_service
        self.model_inference_service = model_inference_service
        self.storage = prediction_repository
        
    async def predict_and_store(self, match_id: int) -> bool:
        input_array: np.ndarry = await self.feature_preparation_service.get_transformed_features_from_id(match_id)
        
        if not input_array:
            logger.warning(f"input array empty after feature preparation for match: {match_id}")
            return False
        try:
            prediction_instance: ModelPrediction = await self.model_inference_service.get_prediction(input_array)
            prediction_list = prediction_instance.prediction
            prediction = prediction_list[0]
            logger.info(f"Successfully fetched prediction for match: {match_id}, value: {prediction}")
        except Exception as e:
            logger.error(f"Error when making prediction for {match_id}: {e}", exc_info=True)
            return False
        
        try:
            metadata = self.model_inference_service.model_metadata
            await self.storage.store_match_prediction(
                match_id=match_id,
                prediction=bool(prediction),
                predictor_name=metadata.name,
                predictor_version=metadata.version
            )
        except Exception as e:
            logger.error(f"Failed to store predictions for match {match_id}: {e}", exc_info=True)
            return False
        
        return True