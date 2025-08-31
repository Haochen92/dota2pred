from fastapi import APIRouter, HTTPException
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api.schema import HeroImageResponse
from ..dependencies import DatabaseSession
from .fetch_image_url import fetch_hero_image_urls

"""
SSE Endpoint
"""


# Instantiate supporting services
logger = get_logger(__name__)

# Instantiate APIrouter
router = APIRouter(
    prefix="/heroes",
    tags=["heroes"],
)


@router.get(
    "/get_image_urls",
    response_model=HeroImageResponse,
    summary="Get hero image URLs - HOT RELOAD TEST",
    status_code=200,
)
async def get_hero_image_urls(
    db_session: DatabaseSession,
    ) -> HeroImageResponse:
    
    try:
        heros_image_data = await fetch_hero_image_urls(db_session)
        if not heros_image_data.heroes:
            raise HTTPException(status_code=404, detail="No hero image data found")
        return heros_image_data
    except Exception as e:
        logger.error(f"Error fetching hero image URLs: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

