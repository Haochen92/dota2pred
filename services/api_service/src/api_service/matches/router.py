from typing import Annotated
from fastapi import APIRouter, Query
from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.pagination import PaginationFilters, PaginatedMatchResponse
from ..dependencies import MatchPaginationSvc

"""
Match API Endpoints
"""

# Instantiate supporting services
logger = get_logger(__name__)

# Instantiate APIrouter
router = APIRouter(
    prefix="/matches",
    tags=["matches"],
)


@router.get("/", response_model=PaginatedMatchResponse)
async def get_matches(
    # All parameters packaged into a single Pydantic model from query parameters
    filters: Annotated[PaginationFilters, Query()],
    pagination_service: MatchPaginationSvc,
) -> PaginatedMatchResponse:
    """
    Get paginated matches with optional filters.

    Returns completed matches in descending order of match ID (latest first).
    You can filter by hero names, patch numbers, and team names.
    """
    return await pagination_service.get_paginated_matches(filters=filters)
