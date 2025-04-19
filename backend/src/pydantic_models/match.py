from pydantic import BaseModel
from typing import Optional

class Match(BaseModel):
    # UUID
    match_id: int
    
    # Team information
    radiant_name: Optional[str] = None
    radiant_team_id: Optional[int] = None
    dire_name: Optional[str] = None
    dire_team_id: Optional[int] = None
    
    # Match metadata
    start_time: Optional[int] = None
    duration: Optional[float] = None
    radiant_win: Optional[bool] = None
    
    # Hero & Player Data
    slot_0_hero_id: Optional[int] = None
    slot_1_hero_id: Optional[int] = None
    slot_2_hero_id: Optional[int] = None
    slot_3_hero_id: Optional[int] = None
    slot_4_hero_id: Optional[int] = None
    slot_128_hero_id: Optional[int] = None
    slot_129_hero_id: Optional[int] = None
    slot_130_hero_id: Optional[int] = None
    slot_131_hero_id: Optional[int] = None
    slot_132_hero_id: Optional[int] = None
    
    slot_0_account_id: Optional[int] = None
    slot_1_account_id: Optional[int] = None
    slot_2_account_id: Optional[int] = None
    slot_3_account_id: Optional[int] = None
    slot_4_account_id: Optional[int] = None
    slot_128_account_id: Optional[int] = None
    slot_129_account_id: Optional[int] = None
    slot_130_account_id: Optional[int] = None
    slot_131_account_id: Optional[int] = None
    slot_132_account_id: Optional[int] = None