from sqlmodel import SQLModel
from dota_oracle.models.live_games.schema import LiveLeagueGame
from dota_oracle.models.redis.schema import StreamMatchEventData
from dota_oracle.models.match import MatchTable

class NewMatchWorkItem(SQLModel):
    """DTO for new match processing work items."""
    live_match_data: LiveLeagueGame
    match_id: int
    

class FeatureEngineeringWorkItem(SQLModel):
    """DTO for feature engineering work items."""
    event_id: str
    event_data: StreamMatchEventData
    match_details: MatchTable

class PredictionWorkItem(SQLModel):
    """DTO for prediction work items."""
    event_id: str
    event_data: StreamMatchEventData
    match_id: int
    
class CompletionWorkItem(SQLModel):
    """DTO for new match Competion work items."""
    event_id: str
    event_data: StreamMatchEventData
    outcome: bool
    