from fastapi import APIRouter, HTTPException, Query
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api.schema import (
    PublicMatchPredictionRequest,
    PublicMatchPredictionResponse,
    ModelHistoryRequest,
    ModelHistoryResponse,
)

from ..dependencies import InferenceSvc, ModelHistorySvc
from typing import Annotated


"""
Inference API Endpoints
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


@router.get(
    "/model_history",
    response_model=ModelHistoryResponse,
    summary="get model performance history",
)
async def get_model_history(
    request: Annotated[ModelHistoryRequest, Query()], model_history_service: ModelHistorySvc
) -> ModelHistoryResponse:
    """Get model performance history.

    Returns:
        ModelHistoryResponse: The model performance history.
    """
    try:
        response = await model_history_service.get_model_performance_history(request)
        return response
    except Exception as e:
        logger.error(f"Error fetching model history: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error, {e}")
