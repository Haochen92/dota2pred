from typing import Dict
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse
from dota_oracle_common.models.api import PublicMatchPredictionRequest, PublicMatchPredictionResponse
from dota_oracle_pipeline.feature_transformation.feature_encoder import FeatureEncoder
import numpy as np

logger = get_logger(__name__)


class PubInferenceService:
    def __init__(
        self,
        model_inference_service: ModelInferenceService,
        feature_encoder: FeatureEncoder,
    ):
        """
        Initializes the PubInferenceService with a model inference service.
        Args:
            model_inference_service: An instance of ModelInferenceService to handle inference logic.
        """
        self.model_inference_service = model_inference_service
        self.feature_encoder = feature_encoder
        self.hero_map = Dict[int, str]

    async def run_inference_cycle(self, raw_inputs_data: PublicMatchPredictionRequest) -> PublicMatchPredictionResponse:
        """
        Runs complete inference cycle, by transforming raw inputs into a prediction.
        1. Transform raw inputs into numpy array
        2. Call model inference service to get prediction
        3. Return prediction as PublicMatchPredictionResponse
        """

        transformed_features = await self.transform_raw_inputs(raw_inputs_data)
        response = await self.get_prediction(transformed_features)

        if not response or not response.prediction:
            raise ValueError("Received empty prediction response from model inference service.")

        predicted_outcome = bool(response.prediction[0])
        predicted_probability = response.probability[0] if response.probability else None

        return PublicMatchPredictionResponse(
            prediction=predicted_outcome,
            probability=predicted_probability,
        )

    async def transform_raw_inputs(self, raw_inputs_data: PublicMatchPredictionRequest) -> np.ndarray:
        transformed_dataframe = self.feature_encoder.transform_single_request(raw_inputs_data)
        return transformed_dataframe.to_numpy()

    async def get_prediction(self, input_features: np.ndarray) -> ModelPredictionAPIResponse:
        try:
            prediction = await self.model_inference_service.get_prediction(input_features)
            return prediction
        except Exception as e:
            logger.error(f"Error during model prediction: {e}")
            raise
