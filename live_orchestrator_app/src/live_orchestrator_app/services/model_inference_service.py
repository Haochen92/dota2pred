import aiohttp
import os
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle_common.utils import get_logger, load_workspace_env
from pydantic import ValidationError
from typing import Optional

logger = get_logger(__name__)
load_workspace_env()


class ModelInferenceService:
    def __init__(self):
        self.base_url = os.getenv("MODEL_ENDPOINT")
        self.predict_url = f"{self.base_url}/predict"
        self.metadata_url = f"{self.base_url}/get_metadata"
        self.session: Optional[aiohttp.ClientSession] = None
        self.model_metadata: Optional[ModelMetaDataAPIResponse] = None

    @classmethod
    async def create(cls) -> "ModelInferenceService":
        """Factory method to create and initialize service with async resources."""
        instance = cls()
        await instance.initialize_async_service()
        return instance

    async def initialize_async_service(self) -> None:
        """Initialize async HTTP session and fetch model metadata."""
        # Create persistent session with appropriate timeout
        timeout = aiohttp.ClientTimeout(total=120, connect=30)  # Generous for cold starts
        self.session = aiohttp.ClientSession(timeout=timeout, headers={"Content-Type": "application/json"})

        # Fetch metadata during initialization
        self.model_metadata = await self.get_model_metadata()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=15, max=60),
        retry=retry_if_exception_type((aiohttp.ClientError, aiohttp.ServerTimeoutError)),
        reraise=True,
    )
    async def get_prediction(self, input_features: np.ndarray) -> ModelPredictionAPIResponse:
        """
        Get prediction from model endpoint with cold start-aware retry strategy.

        Args:
            input_features: Input data for model prediction.

        Returns:
            Validated prediction response from the model.

        Raises:
            aiohttp.ClientError: On network or HTTP errors.
            ValidationError: On response validation failures.
        """
        if not self.session:
            raise RuntimeError("Service not initialized. Use ModelInferenceService.create()")

        logger.info("Calling model endpoint for prediction...")
        request_data = {"input_data": {"input_features": input_features.tolist()}}

        try:
            async with self.session.post(self.predict_url, json=request_data) as response:
                response.raise_for_status()
                result = await response.json()

                try:
                    return ModelPredictionAPIResponse.model_validate(result)
                except ValidationError as ve:
                    logger.error(f"Validation error for prediction response: {ve}", exc_info=True)
                    raise

        except aiohttp.ClientResponseError as ce:
            logger.error(f"HTTP {ce.status} error from {self.predict_url}: {ce.message}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Network error getting prediction: {e}")
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=15, max=60),
        retry=retry_if_exception_type((aiohttp.ClientError, aiohttp.ServerTimeoutError)),
        reraise=True,
    )
    async def get_model_metadata(self) -> ModelMetaDataAPIResponse:
        """
        Fetch model metadata from endpoint with cold start-aware retry strategy.

        Returns:
            Validated metadata response from the model service.

        Raises:
            aiohttp.ClientError: On network or HTTP errors.
            ValidationError: On response validation failures.
            ValueError: If metadata is empty or invalid.
        """
        if not self.session:
            raise RuntimeError("Service not initialized. Use ModelInferenceService.create()")

        try:
            async with self.session.post(self.metadata_url, json={}) as response:
                response.raise_for_status()
                result_dict = await response.json()

                logger.debug("Successfully fetched model metadata")
                validated_metadata = ModelMetaDataAPIResponse.model_validate(result_dict)

                if not validated_metadata:
                    raise ValueError("Received empty model metadata")

                return validated_metadata

        except aiohttp.ClientResponseError as ce:
            logger.error(f"HTTP {ce.status} error from {self.metadata_url}: {ce.message}")
            raise
        except ValidationError as ve:
            logger.error(f"Validation error for metadata response: {ve}", exc_info=True)
            raise
        except aiohttp.ClientError as e:
            logger.error(f"Network error getting metadata: {e}")
            raise

    async def close(self):
        """Gracefully close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
