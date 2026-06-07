from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, TypeVar, Generic, Annotated
from datetime import datetime as dt

PlayerType = TypeVar("PlayerType", bound="Player")
FactionType = TypeVar("FactionType", bound="Faction")


class TeamData(BaseModel):
    """Team information for live games.

    Attributes:
        team_name: Team display name (optional[str])
        team_id: Unique team identifier (int)
    """

    team_name: Optional[str] = None
    team_id: int


class Player(BaseModel):
    """Base PLayer Model for live games

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


class Faction(BaseModel, Generic[PlayerType]):
    """Team faction with player list.

    Attributes:
        players: List of players in faction (List[Player])
    """

    players: List[PlayerType]


class ScoreBoard(BaseModel, Generic[FactionType]):
    """Live game scoreboard data.

    Attributes:
        duration: Match duration in seconds (float)
        radiant: Radiant team faction (Faction)
        dire: Dire team faction (Faction)
    """

    duration: float = 0.0
    radiant: FactionType
    dire: FactionType


class LiveLeagueGame(BaseModel):
    """Live league game data model.
    Description:
        Represents games which has went live,
        but not necessarily started (In Game match duration is 0, ban/pick ongoing.)

    Attributes:
        match_id: Unique match identifier (int)
        league_id: League identifier (int)
        start_time: Game start timestamp (float)
        radiant_team: data on radiant team (Optional[TeamData])
        dire_team: data on dire team (Optional[TeamData])
        scoreboard: live score board of games which started (Optional[Scoreboard])
    """

    match_id: int
    league_id: int
    start_time: float = Field(default_factory=lambda: dt.now().timestamp())
    radiant_team: Optional[TeamData] = None
    dire_team: Optional[TeamData] = None
    scoreboard: Optional[ScoreBoard[Faction[Player]]] = None


class OngoingPlayer(Player):
    """
    Valid hero_id starting from 1 for ongoing matches
    """

    #
    hero_id: int = Field(gt=0)


class OngoingFaction(Faction[OngoingPlayer]):
    players: Annotated[List[OngoingPlayer], Field(min_length=5, max_length=5)]


class OngoingLeagueGame(LiveLeagueGame):
    """Live Games which have finished ban/pick phase.

    Attributes:
        match_id: Unique match identifier (int)
        league_id: League identifier (int)
        start_time: Game start timestamp (float)
        radiant_team: Radiant team data (TeamData)
        dire_team: Dire team data (TeamData)
        scoreboard: Current game scoreboard (ScoreBoard)
    """

    radiant_team: TeamData = Field(...)  # type: ignore
    dire_team: TeamData = Field(...)  # type: ignore
    scoreboard: ScoreBoard[OngoingFaction] = Field(...)  # type: ignore

    @model_validator(mode="after")
    def _heroes_must_be_unique(self) -> "OngoingLeagueGame":
        """Reject drafts where a hero appears more than once across both teams.

        A valid pro draft has 10 distinct heroes. Duplicates indicate a glitched/unparsed
        live-API payload (e.g. the same hero on both teams, or several copies on one team),
        which would otherwise be persisted and later crash the (hero_id, match_id) upsert in
        the completion stage.
        """
        hero_ids = [p.hero_id for p in self.scoreboard.radiant.players + self.scoreboard.dire.players]
        if len(set(hero_ids)) != len(hero_ids):
            raise ValueError(f"Duplicate hero_ids in draft for match {self.match_id}: {sorted(hero_ids)}")
        return self


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
