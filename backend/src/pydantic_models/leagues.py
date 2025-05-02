from pydantic import BaseModel, RootModel
from typing import List, Optional

class LeagueItem(BaseModel):
    leagueid: Optional[int] = None
    tier: Optional[str] = None
    name: Optional[str] = None
    

class LeaguesAPIResponse(RootModel):
    root: List[LeagueItem]