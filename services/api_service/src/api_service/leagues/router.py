from fastapi import APIRouter, HTTPException
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.api.schema import LeagueDataResponse
from ..dependencies import DatabaseSession
from .fetch_leagues_info import fetch_league_info


# Instantiate supporting services
logger = get_logger(__name__)

# Instantiate APIrouter
router = APIRouter(
    prefix="/leagues",
    tags=["leagues"],
)


@router.get(
    "/get_league_info",
    response_model=LeagueDataResponse,
    summary="Get league information",
    status_code=200,
)
async def get_league_info(
    db_session: DatabaseSession,
) -> LeagueDataResponse:

    try:
        leagues_data = await fetch_league_info(db_session)
        if not leagues_data.leagues:
            raise HTTPException(status_code=404, detail="No league data found")
        return leagues_data
    except Exception as e:
        logger.error(f"Error fetching league information: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
