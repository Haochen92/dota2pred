from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, String, TIMESTAMP, Integer, Float
from datetime import datetime


class TeamDecayedStateTable(SQLModel, table=True):
    """Stores the time-decayed state for each team's win rate.

    This table enables efficient O(1) updates for feature generation.
    """

    __tablename__ = "team_decayed_states"

    # Primary key uses team_id for stable identity; keep team_name as optional metadata
    team_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    team_name: str | None = Field(default=None, sa_column=Column(String, nullable=True))

    # The decayed, effective number of wins and games
    decayed_wins: float = Field(sa_column=Column(Float, nullable=False, default=0.0))
    decayed_games: float = Field(sa_column=Column(Float, nullable=False, default=0.0))

    # Timestamp of the last match that updated this state
    last_update_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))


class TeamMatchupDecayedStateTable(SQLModel, table=True):
    """Stores the time-decayed state for each unique team matchup.

    Team1 is always the lexicographically smaller name to ensure uniqueness.
    """

    __tablename__ = "team_matchup_decayed_states"

    # Composite Primary Key for the matchup (IDs); keep names as optional metadata
    team1_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    team2_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    team1_name: str | None = Field(default=None, sa_column=Column(String, nullable=True))
    team2_name: str | None = Field(default=None, sa_column=Column(String, nullable=True))

    # Decayed wins from team1's perspective
    decayed_t1_wins: float = Field(sa_column=Column(Float, nullable=False, default=0.0))
    decayed_games: float = Field(sa_column=Column(Float, nullable=False, default=0.0))

    # Timestamp of the last match that updated this state
    last_update_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))


class HeroDecayedStateTable(SQLModel, table=True):
    """Stores the time-decayed state for each hero's global performance."""

    __tablename__ = "hero_decayed_states"

    # Composite Primary Key
    hero_id: int = Field(sa_column=Column(Integer, primary_key=True))
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True))

    # Decayed wins/games across all matches for this hero
    decayed_wins: float = Field(sa_column=Column(Float, nullable=False, default=0.0))
    decayed_games: float = Field(sa_column=Column(Float, nullable=False, default=0.0))

    # Timestamp of the last match that updated this state
    last_update_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))


class PlayerHeroDecayedStateTable(SQLModel, table=True):
    """Stores the time-decayed state for each unique player-hero combination."""

    __tablename__ = "player_hero_decayed_states"

    # Composite Primary Key
    account_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    hero_id: int = Field(sa_column=Column(Integer, primary_key=True))
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True))

    # The decayed state
    decayed_wins: float = Field(sa_column=Column(Float, nullable=False, default=0.0))
    decayed_games: float = Field(sa_column=Column(Float, nullable=False, default=0.0))

    # Timestamp of the last match that updated this state
    last_update_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
