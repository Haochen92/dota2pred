import aiohttp
import pandas as pd
from typing import List, Union
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from pydantic_models.inference import ModelInferenceAPIResponse
from utils.set_logging import get_logger
from pydantic import ValidationError
from typing import Any

logger = get_logger(__name__)

class ModelInference:
    def __init__(self, engine: AsyncEngine, model_url: str = "http://localhost:3333/predict"):
        self.engine = engine
        self.model_url = model_url

    async def call_model(self, input_features: Any) -> ModelInferenceAPIResponse:
    
        request_data = {"input_data": {"features": input_features}}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.model_url,
                    headers={"Content-Type": "application/json"},
                    json=request_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                       
                    else:
                        print(f"Error: {response.status}")
                        raise ValueError(f"API returned status code {response.status}")
                    
                    validated_result = ModelInferenceAPIResponse.model_validate(result)
                    return validated_result
                    
        except ValidationError as ve:
            logger.error(f"Validation error for returned data {ve}", exc_info=True)
        except Exception as e:
            logger.error(f"Error getting prediction: {e}", exc_info=True)
            raise e
        