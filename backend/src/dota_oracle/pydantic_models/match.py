from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

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
    

class Match(BaseModel):
    # UUID
    match_id: int
    
    # league information
    leagueid: Optional[int] = None
    
    # Team information
    radiant_name: Optional[str] = None
    radiant_team_id: int
    dire_name: Optional[str] = None
    dire_team_id: int
    
    # Match metadata
    start_time: datetime
    duration: Optional[float] = None
    radiant_win: Optional[bool] = None
    
    # Hero & Player Data
    slot_0_hero_id: str
    slot_1_hero_id: str
    slot_2_hero_id: str
    slot_3_hero_id: str
    slot_4_hero_id: str
    slot_128_hero_id: str
    slot_129_hero_id: str
    slot_130_hero_id: str
    slot_131_hero_id: str
    slot_132_hero_id: str
    
    slot_0_account_id: int
    slot_1_account_id: int
    slot_2_account_id: int
    slot_3_account_id: int
    slot_4_account_id: int
    slot_128_account_id: int
    slot_129_account_id: int
    slot_130_account_id: int
    slot_131_account_id: int
    slot_132_account_id: int