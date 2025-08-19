from fastapi import APIRouter
from typing import Dict, Any
from dota_oracle_common.utils import get_logger
import httpx

"""
SSE Endpoint
"""


# Instantiate supporting services
logger = get_logger(__name__)

# Instantiate APIrouter
router = APIRouter(
    prefix="/matchtable",
    tags=["matchtable"],
)


@router.post("/predict")
async def predict(data: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.post("http://prediction-service:3000/predict", json=data)
        result: Dict[str, Any] = response.json()
        return result
