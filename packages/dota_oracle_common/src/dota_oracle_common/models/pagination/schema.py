from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..match.schema import CompletedMatchAPIPayload


class PaginationFilters(BaseModel):
    """Comprehensive match filters including pagination and all filter options."""

    model_config = ConfigDict(populate_by_name=True)

    # Pagination parameters
    page: Optional[int] = Field(1, ge=1, description="Page number (1-indexed) - Legacy, use offset/limit instead")
    page_size: Optional[int] = Field(
        20, ge=10, le=50, description="Items per page (10-50) - Legacy, use offset/limit instead"
    )
    offset: Optional[int] = Field(None, ge=0, description="Offset for pagination (alternative to page), 0-indexed")
    limit: Optional[int] = Field(None, ge=0, le=50, description="Limit for pagination (alternative to page_size), 0-50")

    # Basic filters
    match_id: Optional[int] = Field(None, description="Filter by specific match ID")
    patch_number: Optional[str] = Field(None, description="Filter by patch number (e.g., '7.35')")
    team_name: Optional[str] = Field(None, description="Filter by team name (partial match)")
    league_id: Optional[int] = Field(None, description="Filter by league ID (exact match)")

    # User-facing filters (from query parameters)
    team_ids: Optional[List[int]] = Field(None, description="Filter by a list of team IDs", alias="team_ids[]")
    hero_ids: Optional[List[int]] = Field(None, description="Filter by a list of hero IDs", alias="hero_ids[]")

    # Internal resolved filters (populated by service layer)
    patch_start_time: Optional[datetime] = None
    patch_end_time: Optional[datetime] = None


class PaginatedMatchResponse(BaseModel):
    """Response model for paginated matches"""

    matches: List[CompletedMatchAPIPayload]
    total_count: int
    total_pages: int
    page: Optional[int] = None
    page_size: Optional[int] = None
    has_next: Optional[bool] = None
    has_previous: Optional[bool] = None

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2
