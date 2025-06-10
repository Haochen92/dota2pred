from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime as dt
    
class TeamData(BaseModel):
    """Team information for live games.
    
    Attributes:
        team_name: Team display name (str)
        team_id: Unique team identifier (int)
    """
    team_name: str
    team_id: int

class Player(BaseModel):
    """Player data in live games.
    
    Attributes:
        player_slot: Player slot position (int)
        account_id: Player account identifier (int)
        name: Player display name (Optional[str])
        hero_id: Selected hero identifier (int)
    """
    player_slot: int 
    account_id: int 
    name: Optional[str] = None
    hero_id: int 

class Faction(BaseModel):
    """Team faction with player list.
    
    Attributes:
        players: List of players in faction (List[Player])
    """
    players: List[Player]
    
class ScoreBoard(BaseModel):
    """Live game scoreboard data.
    
    Attributes:
        duration: Match duration in seconds (float)
        radiant: Radiant team faction (Faction)
        dire: Dire team faction (Faction)
    """
    duration: float = 0.0
    radiant: Faction
    dire: Faction

class LiveLeagueGame(BaseModel):
    """Live league game data model.
    
    Attributes:
        match_id: Unique match identifier (int)
        league_id: League identifier (int)
        start_time: Game start timestamp (float)
        radiant_team: Radiant team data (TeamData)
        dire_team: Dire team data (TeamData)
        scoreboard: Current game scoreboard (ScoreBoard)
    """
    match_id: int
    league_id: int
    start_time: float = Field(default_factory=lambda: dt.now().timestamp())
    radiant_team: TeamData
    dire_team: TeamData
    scoreboard: ScoreBoard

class ResultData(BaseModel):
    """Container for live games list.
    
    Attributes:
        games: List of live league games (List[LiveLeagueGame])
    """
    games: List[LiveLeagueGame] = []
    
class LiveLeagueAPIResponse(BaseModel):
    """API response for live league games.
    
    Attributes:
        result: Live games result data (ResultData)
    """
    result: ResultData