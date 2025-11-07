import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse
from dota_oracle_common.models.api import PublicMatchPredictionRequest, PublicMatchPredictionResponse
from dota_oracle_common.models.api.schema import PublicMatchPredictionDTO
from dota_oracle_common.utils.time_utils import get_current_utc_iso_timestamp
from dota_oracle_pipeline.inference.model_inference_service import ModelInferenceService
from dota_oracle_pipeline.feature_engineering.public_inference_features import (
    create_public_inference_features,
)

logger = get_logger(__name__)


"""
We normalize the request to PublicMatchPredictionDTO (list-based heroes) and
delegate feature building to a public-only feature creator that fetches decayed
hero states and aggregates them for model input.
"""


class PubInferenceService:
    def __init__(
        self,
        model_inference_service: ModelInferenceService,
        db_session_factory: async_sessionmaker[AsyncSession],
    ):
        """
        Initializes the PubInferenceService with a model inference service.
        Args:
            model_inference_service: An instance of ModelInferenceService to handle inference logic.
            db_session_factory: An async session maker for database interactions.
        """
        self.model_inference_service = model_inference_service
        self.db_session_factory = db_session_factory

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
        """Build model-ready features for the public model.

        Normalizes the API request into PublicMatchPredictionDTO and delegates
        computation to the public feature builder which derives per-hero
        time-decayed win rates directly from recent PublicMatchTable rows.
        Returns a (1 x n_features) numpy array (currently n_features=1).
        """
        # Normalize to DTO for internal consistency
        if isinstance(raw_inputs_data, PublicMatchPredictionDTO):
            dto = raw_inputs_data
        else:
            dto = PublicMatchPredictionDTO(
                match_id=0,
                start_time=get_current_utc_iso_timestamp(),
                **raw_inputs_data.model_dump(),
            )

        async with self.db_session_factory() as session:
            return await create_public_inference_features(session, dto)

    async def get_prediction(self, input_features: np.ndarray) -> ModelPredictionAPIResponse:
        try:
            prediction = await self.model_inference_service.get_prediction(input_features)
            return prediction
        except Exception as e:
            logger.error(f"Error during model prediction: {e}")
            raise
