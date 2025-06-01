from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
    
    
class MatchOutcome(BaseModel):
    match_id: int
    radiant_win: bool
    
    
class MatchWithOutcome(Match):
    radiant_win: bool
    
