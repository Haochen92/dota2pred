import httpx
import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from dota_oracle_common.models.inference.schema import (
    ModelPredictionAPIResponse,
    ModelMetaDataAPIResponse,
    PredictionInputPayload,
)
from dota_oracle_common.utils import get_logger
from pydantic import ValidationError

from dota_oracle_common.utils.retry_utils import is_retryable_error

logger = get_logger(__name__)


class ModelInferenceService:
    """A stateless service for performing model inference operations.

    This service is designed for use with dependency injection. It encapsulates the
    logic for communicating with a remote model prediction endpoint. An `httpx.AsyncClient`
    and the model's metadata are injected upon initialization to allow for persistent
    connections and pre-configured model information.

    Attributes:
        http_client (httpx.AsyncClient): An asynchronous HTTP client for making requests.
        prediction_url (str): The URL of the model's prediction endpoint.
        model_metadata (ModelMetaDataAPIResponse): Pre-fetched metadata about the model,
            such as its version and feature details.
    """

    def __init__(self, http_client: httpx.AsyncClient, model_metadata: ModelMetaDataAPIResponse, prediction_url: str):
        """Initializes the ModelInferenceService.

        Args:
            http_client: An initialized and persistent `httpx.AsyncClient` instance.
            model_metadata: A Pydantic model containing the metadata of the target model.
            prediction_url: The full URL to the prediction endpoint.
        """
        self.http_client = http_client
        self.prediction_url = prediction_url
        self.model_metadata = model_metadata

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=15, max=60),
        retry=retry_if_exception(is_retryable_error),
        reraise=True,
    )
    async def get_prediction(self, input_features: np.ndarray) -> ModelPredictionAPIResponse:
        """Fetches a prediction from the remote model inference endpoint.

        This method sends the provided input features to the configured prediction URL,
        awaits the response, and validates it against the `ModelPredictionAPIResponse` schema.

        Note:
            This method includes automatic retries with exponential backoff for
            retryable HTTP errors (e.g., 5xx status codes, network issues)
            as defined by the `is_retryable_error` function.

        Args:
            input_features: A NumPy array containing the input features for the model.
                The shape should match the model's expected input dimensions.

        Returns:
            A `ModelPredictionAPIResponse` object containing the structured model
            prediction and associated metadata from the API.

        Raises:
            httpx.HTTPStatusError: If the API returns a 4xx or 5xx client/server
                error status code after all retry attempts have been exhausted.
            httpx.RequestError: For fundamental network issues like a connection
                error or timeout after all retries.
            pydantic.ValidationError: If the JSON response from the API does not
                conform to the `ModelPredictionAPIResponse` Pydantic model schema.
        """
        url = self.prediction_url
        logger.info(f"Calling model endpoint for prediction: {url}")

        # Validate payload using Pydantic model before sending
        payload = PredictionInputPayload(input_features=input_features.tolist())
        # BentoML expects the payload to be wrapped in a 'data' field
        request_data = {"data": payload.model_dump()}

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
    async def fetch_model_metadata(http_client: httpx.AsyncClient, metadata_url: str) -> ModelMetaDataAPIResponse:
        """Fetches model metadata from a remote metadata endpoint.

        This static utility method is intended to be used during application
        startup or container initialization to retrieve the necessary metadata
        required to instantiate the `ModelInferenceService`.

        Note:
            Like `get_prediction`, this method also includes automatic retries
            with exponential backoff for retryable HTTP errors.

        Args:
            http_client: An `httpx.AsyncClient` instance to use for the request.
            metadata_url: The URL of the model's metadata endpoint.

        Returns:
            A `ModelMetaDataAPIResponse` object containing the model's version,
            feature names, and other relevant metadata.

        Raises:
            httpx.HTTPStatusError: If the API returns a 4xx or 5xx status code.
            httpx.RequestError: For network issues like connection errors.
            pydantic.ValidationError: If the API response does not match the
                `ModelMetaDataAPIResponse` schema.
        """
        try:
            response = await http_client.post(metadata_url, json={})
            response.raise_for_status()
            return ModelMetaDataAPIResponse.model_validate(response.json())
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.error(f"Error during fetch_model_metadata API call: {exc}")
            raise
