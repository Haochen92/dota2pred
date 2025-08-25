from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from ..match.schema import CompletedMatchAPIPayload


class PaginationFilters(BaseModel):
    """Comprehensive match filters including pagination and all filter options."""

    model_config = ConfigDict(populate_by_name=True)

    # Pagination parameters
    page: int = Field(1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(20, ge=1, le=100, description="Items per page (1-100)")

    # Basic filters
    match_id: Optional[int] = Field(None, description="Filter by specific match ID")
    patch_number: Optional[str] = Field(None, description="Filter by patch number (e.g., '7.35')")
    team_name: Optional[str] = Field(None, description="Filter by team name (partial match)")

    # User-facing filters (from query parameters)
    team_ids: Optional[List[int]] = Field(None, description="Filter by a list of team IDs", alias="team_ids[]")
    hero_names: Optional[List[str]] = Field(None, description="Filter by a list of hero names", alias="hero_names[]")

    # Internal resolved filters (populated by service layer)
    hero_ids: Optional[List[int]] = None
    patch_start_time: Optional[datetime] = None
    patch_end_time: Optional[datetime] = None


class PaginatedMatchResponse(BaseModel):
    """Response model for paginated matches"""

    matches: List[CompletedMatchAPIPayload]
    total_count: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

    class Config:
        from_attributes = True  # Updated from orm_mode for Pydantic v2
