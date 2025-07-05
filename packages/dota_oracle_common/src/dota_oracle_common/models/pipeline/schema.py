from sqlmodel import SQLModel
from ..live_games.schema import OngoingLeagueGame
from ..redis.schema import StreamMatchEventData
from ..match import MatchTable


class NewMatchWorkItem(SQLModel):
    """
    DTO for new match processing work items.

    Attributes:
        live_match_data: OngoingLeagueGame -> live games which have started (after ban/pick phase)
        match_id: int -> unique identifier for a match
    """

    live_match_data: OngoingLeagueGame
    match_id: int


class FeatureEngineeringWorkItem(SQLModel):
    """
    DTO for feature engineering work items.

    Attributes:
        event_id: str -> a string representing event_id from a redis Stream
        event_data: StreamMatchEventData -> event data from a redis Stream
        match_details: MatchTable -> MatchTable
    """

    event_id: str
    event_data: StreamMatchEventData
    match_details: MatchTable


class PredictionWorkItem(SQLModel):
    """
    DTO for prediction work items.

    Attributes:
        event_id: str -> a string representing event_id from a redis Stream
        event_data: StreamMatchEventData -> event data from a redis Stream
        match_details: MatchTable -> MatchTable
    """

    event_id: str
    event_data: StreamMatchEventData
    match_id: int


class CompletionWorkItem(SQLModel):
    """
    DTO for new match Competion work items.
        Attributes:
        event_id: str -> a string representing event_id from a redis Stream
        event_data: StreamMatchEventData -> event data from a redis Stream
        match_details: MatchTable -> MatchTable
    """

    event_id: str
    event_data: StreamMatchEventData
    outcome: bool
