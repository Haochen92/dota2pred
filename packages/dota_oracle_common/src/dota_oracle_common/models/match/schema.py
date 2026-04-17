from pydantic import BaseModel, RootModel
from typing import Optional, List
from .base import Match, MatchWithOutcome


class LeagueData(BaseModel):
    """League information for matches.

    Attributes:
        leagueid: League identifier (Optional[int])
        tier: League tier level (Optional[str])
        name: League display name (Optional[str])
    """

    leagueid: Optional[int] = None
    tier: Optional[str] = None
    name: Optional[str] = None


class PlayerData(BaseModel):
    """Player data in match context.

    Attributes:
        player_slot: Player slot position (int)
        account_id: Player account identifier (int)
        hero_id: Selected hero identifier (int)
        name: Player display name (Optional[str])
    """

    player_slot: int
    account_id: int
    hero_id: int
    name: Optional[str] = None


class MatchesAPIResponse(BaseModel):
    """API response for match data.

    Attributes:
        match_id: Unique match identifier (int)
        start_time: Match start timestamp (int)
        duration: Match duration in seconds (float)
        radiant_win: Whether radiant team won (bool)
        radiant_name: Radiant team name (Optional[str])
        radiant_team_id: Radiant team identifier (Optional[int])
        dire_name: Dire team name (Optional[str])
        dire_team_id: Dire team identifier (Optional[int])
        league: League information (LeagueData)
        players: List of players in match (List[PlayerData])
    """

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

    # league information
    leagueid: Optional[int] = None
    league: Optional[LeagueData] = None

    # Players and Picks
    players: List[PlayerData]


class ProMatchOutcome(BaseModel):
    """Professional match outcome data.

    Attributes:
        match_id: Match identifier (int)
        radiant_win: Whether radiant won (bool)
    """

    match_id: int
    radiant_win: Optional[bool] = None


class ProMatchAPIResponse(RootModel[List[ProMatchOutcome]]):
    """API response for professional match outcomes.

    Attributes:
        root: List of pro match outcomes (List[ProMatchOutcome])
    """

    root: List[ProMatchOutcome]


# API Payloads DTO


class MatchNotifcationAPIPayload(Match):
    """Match model combined with prediction data.

    Inherits from Match and adds prediciton result

    Attributes:
        model_prediction: predicted outcome for the match
    """

    predicted_outcome: Optional[bool] = None
    league_data: Optional[LeagueData] = None


class CompletedMatchAPIPayload(MatchWithOutcome):
    """Completed Match with predictions and actual outcome
    Inherits from Match with Outcome and add prediction results
    """

    predicted_outcome: Optional[bool] = None
    league_data: Optional[LeagueData] = None


class PublicMatch(BaseModel):
    """
    Parsed Match Data from Opendota publicMatches Endpoint

    Fields:
    match_id: int (UUID of match)
    start_time: int (Unix Timestamp of match start time)
    duration: int (Duration of game in seconds)
    avg_rank_tier:int (A numerical representation of the match's skill bracket)


    radiant_team: List[int] (A List of integers representing hero ids in team radiant)
    dire_team: List[int] (A List of integers representing hero ids in team dire)
    """

    match_id: int
    start_time: int
    duration: int
    avg_rank_tier: int
    num_rank_tier: int
    radiant_win: bool

    radiant_team: List[int]
    dire_team: List[int]


class PublicMatchAPIResponse(RootModel[List[PublicMatch]]):
    """
    API response from Opendota's PublicMatch endpoint
    """

    root: List[PublicMatch]
