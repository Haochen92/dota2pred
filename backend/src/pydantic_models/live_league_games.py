from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime as dt
    
class TeamData(BaseModel):
    team_name: str
    team_id: int

class Player(BaseModel):
    player_slot: int 
    account_id: int 
    name: Optional[str] = None
    hero_id: int 

class Faction(BaseModel):
    players: List[Player]
    
class ScoreBoard(BaseModel):
    duration: float = 0.0
    radiant: Faction
    dire: Faction

class LiveLeagueGame(BaseModel):
    match_id: int
    league_id: int
    start_time: float = Field(default_factory=lambda: dt.now().timestamp())
    radiant_team: TeamData
    dire_team: TeamData
    scoreboard: ScoreBoard

class ResultData(BaseModel):
    games: List[LiveLeagueGame] = []
    
class LiveLeagueAPIResponse(BaseModel):
    result: ResultData