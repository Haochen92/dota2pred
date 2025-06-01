from pydantic import BaseModel
from typing import Optional, List

class LeagueData(BaseModel):
    leagueid: Optional[int] = None
    tier: Optional[str] = None
    name: Optional[str] = None  
    
class PlayerData(BaseModel):
    player_slot: int
    account_id: int
    hero_id: int
    name: Optional[str] = None

class MatchesAPIResponse(BaseModel):
    # Match metadata
    match_id: int
    start_time: int
    duration: float
    radiant_win: bool
    
    # team information   
    radiant_name: Optional[str] = None
    radiant_team_id: Optional[int] = None
    dire_name: Optional[str] = None
    dire_team_id: Optional[int] = None
    
    league: LeagueData
    players: List[PlayerData]

