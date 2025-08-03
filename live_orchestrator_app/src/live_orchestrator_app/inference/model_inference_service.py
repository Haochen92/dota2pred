import aiohttp
import os
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle_common.utils import get_logger, load_workspace_env
from pydantic import ValidationError

logger = get_logger(__name__)
load_workspace_env()


class ModelInferenceService:
    def __init__(self):
        self.base_url = os.getenv("MODEL_ENDPOINT")
        self.predict_url = f"{self.base_url}/predict"
        self.metadata_url = f"{self.base_url}/get_metadata"

    @classmethod
    async def create(cls) -> "ModelInferenceService":
        # Factory class method to create and initialize service
        instance = cls()
        await instance.initialize_async_service()
        return instance

    async def initialize_async_service(self) -> None:
        # Initialize async service
        try:
            self.model_metadata = await self.get_model_metadata()
        except Exception as e:
            raise e

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(),
        retry=retry_if_exception_type(aiohttp.ClientError),
        reraise=True,
    )
    async def get_prediction(self, input_features: np.ndarray) -> ModelPredictionAPIResponse:

        logger.info("calling model endpoint for prediction...")
        request_data = {"input_data": {"input_features": input_features.tolist()}}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.predict_url, headers={"Content-Type": "application/json"}, json=request_data
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    try:
                        validated_result = ModelPredictionAPIResponse.model_validate(result)
                    except ValidationError as ve:
                        error_msg = f"""
                        Validation Error for returned data
                        response data: {result},
                        error: {ve}
                        """
                        logger.error(error_msg, exc_info=True)
                        raise ve
                    return validated_result
        except aiohttp.ClientResponseError as ce:
            logger.error(f"HTTP error {ce.status} getting prediction {self.predict_url}: {ce.message}", exc_info=True)
            raise ce
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            raise e

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(),
        retry=retry_if_exception_type(aiohttp.ClientError),
        reraise=True,
    )
    async def get_model_metadata(self) -> ModelMetaDataAPIResponse:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.metadata_url, json={}, headers={"Accept": "application/json"}) as response:
                    response.raise_for_status()
                    result_dict = await response.json()

                    logger.debug("Successfully fetched metadata")
                    validated_metadata = ModelMetaDataAPIResponse.model_validate(result_dict)

                    if not validated_metadata:
                        raise ValueError("Missing model metadata")

                    return validated_metadata
        except aiohttp.ClientResponseError as ce:
            logger.error(
                f"HTTP error {ce.status} fetching metadata from {self.metadata_url}: {ce.message}", exc_info=True
            )
            raise ce
        except ValidationError as ve:
            logger.error(f"Validation error for returned data {ve}", exc_info=True)
            raise ve
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            raise e
