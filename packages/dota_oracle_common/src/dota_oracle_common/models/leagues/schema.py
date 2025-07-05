from pydantic import BaseModel, RootModel
from typing import List, Optional


class LeagueItem(BaseModel):
    """Individual league data model.

    Attributes:
        leagueid: Unique league identifier (int)
        tier: League tier/level (Optional[str])
        name: League display name (Optional[str])
    """

    leagueid: int
    tier: Optional[str] = None
    name: Optional[str] = None


class LeaguesAPIResponse(RootModel[List[LeagueItem]]):
    """API response model for leagues list.

    Attributes:
        root: List of league items (List[LeagueItem])
    """

    root: List[LeagueItem]
