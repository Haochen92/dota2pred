import aiohttp
import numpy as np
from pydantic_models.inference import ModelPrediction, ModelMetaData
from utils.set_logging import get_logger
from pydantic import ValidationError
from typing import Optional

logger = get_logger(__name__)

class ModelInferenceService:
    def __init__(self):
        self.predict_url = "http://localhost:3333/predict"
        self.metadata_url = "http://localhost:3333/get_metadata"
        
    async def initialize_async_service(self):
        # Initialize async service
        self.model_metadata: ModelMetaData = await self.get_model_metadata()

    async def get_prediction(self, input_features: np.ndarray) -> ModelPrediction:
        
        logger.info(f"calling model endpoint for prediction...")
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
                    validated_result = ModelPrediction.model_validate(result)
                    return validated_result
        except aiohttp.ClientResponseError as ce:
            logger.error(f"HTTP error {ce.status} getting prediction {self.predict_url}: {e.message}", exc_info=True)           
        except ValidationError as ve:
            logger.error(f"Validation error for returned data {ve}", exc_info=True)
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            raise e
    
    async def get_model_metadata(self) -> Optional[ModelMetaData]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.metadata_url,
                    headers={"Accept": "application/json"}
                ) as response:
                    response.raise_for_status()
                    result_dict = await response.json()
                    
                    logger.debug("Successfully fetched metadata")
                    validated_metadata = ModelMetaData.model_validate(result_dict)
                    
                    return validated_metadata
        except aiohttp.ClientResponseError as ce:
            logger.error(f"HTTP error {ce.status} fetching metadata from {self.metadata_url}: {e.message}", exc_info=True)
        except ValidationError as ve:
            logger.error(f"Validation error for returned data {ve}", exc_info=True)
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            raise e