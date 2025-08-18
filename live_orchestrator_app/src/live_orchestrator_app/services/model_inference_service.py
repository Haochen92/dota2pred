import httpx
import os
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle_common.utils import get_logger
from pydantic import ValidationError

from dota_oracle_common.utils.retry_utils import is_retryable_error

logger = get_logger(__name__)


class ModelInferenceService:
    """Stateless service for model inference operations using dependency injection."""

    def __init__(self, http_client: httpx.AsyncClient, model_metadata: ModelMetaDataAPIResponse):
        self.http_client = http_client
        self.base_url = os.getenv("MODEL_ENDPOINT")
        self.model_metadata = model_metadata  # Injected directly!

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=15, max=60),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    async def get_prediction(self, input_features: np.ndarray) -> ModelPredictionAPIResponse:
        """Get prediction from model endpoint using the injected persistent client."""
        url = f"{self.base_url}/predict/pro"
        logger.info(f"Calling model endpoint for prediction: {url}")
        request_data = {"input_data": {"input_features": input_features.tolist()}}

        try:
            response = await self.http_client.post(url, json=request_data)
            response.raise_for_status()
            return ModelPredictionAPIResponse.model_validate(response.json())
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(f"Error during get_prediction API call: {exc}")
            raise
        except ValidationError as ve:
            logger.error(f"Validation error for prediction response: {ve}", exc_info=True)
            raise

    @staticmethod
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=15, max=60),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    async def fetch_model_metadata(http_client: httpx.AsyncClient) -> ModelMetaDataAPIResponse:
        """Static helper to fetch model metadata. Used during container initialization."""
        base_url = os.getenv("MODEL_ENDPOINT")
        url = f"{base_url}/metadata/pro"
        try:
            response = await http_client.post(url, json={})
            response.raise_for_status()
            return ModelMetaDataAPIResponse.model_validate(response.json())
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(f"Error during fetch_model_metadata API call: {exc}")
            raise
