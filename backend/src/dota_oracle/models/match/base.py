from sqlmodel import SQLModel
from typing import Optional
from datetime import datetime

class Match(SQLModel):
    """Base match model with core match data.
    
    Attributes:
        match_id: Unique match identifier (int)
        leagueid: League identifier (Optional[int])
        radiant_name, dire_name: Team names (Optional[str])
        radiant_team_id, dire_team_id: Team identifiers (int)
        start_time: Match start time (datetime)
        duration: Match duration in seconds (Optional[float])
        slot_*_hero_id: Hero IDs for all 10 player slots (str)
        slot_*_account_id: Account IDs for all 10 player slots (int)
    """
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
    
    
class MatchOutcome(SQLModel):
    """Match outcome model.
    
    Attributes:
        match_id: Match identifier (int)
        radiant_win: Whether radiant team won (bool)
    """
    match_id: int
    radiant_win: bool
    
    
class MatchWithOutcome(Match):
    """Match model combined with outcome data.
    
    Inherits from Match and adds outcome information.
    
    Attributes:
        radiant_win: Whether radiant team won (bool)
    """
    radiant_win: bool
    
