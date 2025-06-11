import aiohttp
import numpy as np
from dota_oracle.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle.utils.set_logging import get_logger
from pydantic import ValidationError

logger = get_logger(__name__)

class ModelInferenceService:
    def __init__(self):
        self.predict_url = "http://localhost:3333/predict"
        self.metadata_url = "http://localhost:3333/get_metadata"
        self.model_metadata = None
        
    @classmethod
    async def create(cls):
        # Factory class method to create and initialize service
        instance = cls()
        await instance.initialize_async_service()
        return instance
        
    async def initialize_async_service(self):
        # Initialize async service
        try:
            self.model_metadata = await self.get_model_metadata()
        except Exception as e:
            raise e

    async def get_prediction(self, input_features: np.ndarray) -> ModelPredictionAPIResponse:
        
        logger.info("calling model endpoint for prediction...")
        request_data = {"input_data": {"features": input_features.tolist()}}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.predict_url,
                    headers={"Content-Type": "application/json"},
                    json=request_data
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    validated_result = ModelPredictionAPIResponse.model_validate(result)
                    return validated_result
        except aiohttp.ClientResponseError as ce:
            logger.error(f"HTTP error {ce.status} getting prediction {self.predict_url}: {ce.message}", exc_info=True)  
            raise ce         
        except ValidationError as ve:
            logger.error(f"Validation error for returned data {ve}", exc_info=True)
            raise ve
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            raise e
    
    async def get_model_metadata(self) -> ModelMetaDataAPIResponse:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.metadata_url,
                    json={},
                    headers={"Accept": "application/json"}
                ) as response:
                    response.raise_for_status()
                    result_dict = await response.json()
                    
                    logger.debug("Successfully fetched metadata")
                    validated_metadata = ModelMetaDataAPIResponse.model_validate(result_dict)
                    
                    if not validated_metadata:
                        raise ValueError("Missing model metadata")
                    
                    return validated_metadata
        except aiohttp.ClientResponseError as ce:
            logger.error(f"HTTP error {ce.status} fetching metadata from {self.metadata_url}: {ce.message}", exc_info=True)
            raise ce
        except ValidationError as ve:
            logger.error(f"Validation error for returned data {ve}", exc_info=True)
            raise ve
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            raise e