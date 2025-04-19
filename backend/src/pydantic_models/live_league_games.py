from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime as dt
    
class TeamData(BaseModel):
    team_name: Optional[str] = None
    team_id: Optional[int] = None

class Player(BaseModel):
    player_slot: int 
    account_id: int
    hero_id: int

class Faction(BaseModel):
    players: List[Player]
    
class ScoreBoard(BaseModel):
    duration: Optional[float] = None
    radiant: Faction
    dire: Faction

class LiveLeagueGames(BaseModel):
    match_id: int
    league_id: int
    start_time: float = Field(default_factory=lambda: dt.now().timestamp())
    radiant_team: Optional[TeamData] = None
    dire_team: Optional[TeamData] = None
    scoreboard: Optional[ScoreBoard] = None
