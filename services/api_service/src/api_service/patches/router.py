from fastapi import APIRouter, HTTPException
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api.schema import PatchDataAPIResponse
from ..dependencies import DatabaseSession
from .fetch_patch_data import fetch_patch_ids


logger = get_logger(__name__)

router = APIRouter(
    prefix="/patches",
    tags=["patches"],
)


@router.get(
    "/ids",
    response_model=PatchDataAPIResponse,
    summary="Get list of available patch identifiers",
    status_code=200,
)
async def get_patch_ids(db_session: DatabaseSession) -> PatchDataAPIResponse:
    try:
        response = await fetch_patch_ids(db_session)
        if not response.patches:
            raise HTTPException(status_code=404, detail="No patch data found")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching patch ids: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
