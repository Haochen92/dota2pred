from pydantic import BaseModel, RootModel
from typing import Optional, List


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

    league: LeagueData
    players: List[PlayerData]


class ProMatchOutcome(BaseModel):
    """Professional match outcome data.

    Attributes:
        match_id: Match identifier (int)
        radiant_win: Whether radiant won (bool)
    """

    match_id: int
    radiant_win: bool


class ProMatchAPIResponse(RootModel[List[ProMatchOutcome]]):
    """API response for professional match outcomes.

    Attributes:
        root: List of pro match outcomes (List[ProMatchOutcome])
    """

    root: List[ProMatchOutcome]
