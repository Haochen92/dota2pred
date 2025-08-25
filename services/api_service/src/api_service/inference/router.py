from fastapi import APIRouter, HTTPException
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api import PublicMatchPredictionRequest, PublicMatchPredictionResponse
from ..dependencies import InferenceSvc


"""
SSE Endpoint
"""


# Instantiate supporting services
logger = get_logger(__name__)

# Instantiate APIrouter
router = APIRouter(
    prefix="/inference",
    tags=["inference"],
)


@router.post(
    "/predict",
    response_model=PublicMatchPredictionResponse,
    summary="Predict match outcome based on hero picks",
)
async def predict(data: PublicMatchPredictionRequest, inference_service: InferenceSvc) -> PublicMatchPredictionResponse:
    try:
        response = await inference_service.run_inference_cycle(data)
        return response
    except Exception as e:
        logger.error(f"Error during inference: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error, {e}")
