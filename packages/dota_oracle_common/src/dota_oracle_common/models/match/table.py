from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, Relationship
from sqlalchemy import BigInteger, Column, TIMESTAMP, ForeignKey, Integer, Boolean, Index
from datetime import datetime
from .base import Match, MatchOutcome
from sqlmodel import SQLModel

if TYPE_CHECKING:
    from ..inference.table import MatchPredictionTable
    from ..features.table import TeamFeaturesTable, PlayerHeroFeatureTable, HeroFeaturesTable
    from ..leagues.table import LeagueTable


class MatchTable(Match, table=True):
    """Database table for match data.

    Inherits from Match with database-specific field overrides.

    Attributes:
        match_id: Primary key match identifier (BigInteger)
        slot_*_account_id: Player account IDs for all 10 slots (BigInteger)
        radiant_team_id, dire_team_id: Team identifiers (BigInteger)
        start_time: Match start with timezone support (TIMESTAMP)

    Relationships:
        outcome: Related match outcome (Optional[MatchOutcomeTable])
        predictions: List of match predictions (List[MatchPredictionTable])
        team_features: Team-based features (Optional[TeamFeaturesTable])
        player_hero_features: Player-hero features (Optional[PlayerHeroFeatureTable])
        hero_features: Hero-based features (Optional[HeroFeaturesTable])
        league_data: Associated League information(Optional[LeagueTable])
    """

    __tablename__ = "matches"
    # Primary Key
    match_id: int = Field(sa_column=Column("match_id", BigInteger, primary_key=True))

    # Foreign Keys
    leagueid: Optional[int] = Field(
        default=None, sa_column=Column(Integer, ForeignKey("leaguetable.leagueid"), nullable=True)
    )

    # Columns for account IDs:
    slot_0_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_1_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_2_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_3_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_4_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_128_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_129_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_130_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_131_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    slot_132_account_id: int = Field(sa_column=Column(BigInteger, nullable=False))

    radiant_team_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    dire_team_id: int = Field(sa_column=Column(BigInteger, nullable=False))

    start_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))

    # Relationships
    outcome: Optional["MatchOutcomeTable"] = Relationship(
        back_populates="match", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )
    predictions: List["MatchPredictionTable"] = Relationship(
        back_populates="match", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

    team_features: Optional["TeamFeaturesTable"] = Relationship(
        back_populates="match", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )
    player_hero_features: Optional["PlayerHeroFeatureTable"] = Relationship(
        back_populates="match", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )
    hero_features: Optional["HeroFeaturesTable"] = Relationship(
        back_populates="match", sa_relationship_kwargs={"uselist": False, "cascade": "all, delete-orphan"}
    )

    league_data: Optional["LeagueTable"] = Relationship(
        back_populates="matches", sa_relationship_kwargs={"uselist": False}
    )


class MatchOutcomeTable(MatchOutcome, table=True):
    """Database table for match outcomes.

    Inherits from MatchOutcome with database-specific fields.

    Attributes:
        match_id: Foreign key to matches table (BigInteger, primary key)

    Relationships:
        match: Related MatchTable instance
    """

    __tablename__ = "match_outcomes"

    match_id: int = Field(sa_column=Column(BigInteger, ForeignKey("matches.match_id"), primary_key=True))

    # Relationship
    match: "MatchTable" = Relationship(back_populates="outcome")


class PublicMatchTable(SQLModel, table=True):
    """Database table for high-MMR public matches (minimal fields).

    Columns mirror the simplified `PublicMatch` schema and align hero slots
    with the pro `MatchTable` convention (0-4 radiant, 128-132 dire).
    """

    __tablename__ = "public_matches"

    # Primary Key
    match_id: int = Field(sa_column=Column("match_id", BigInteger, primary_key=True))

    # Metadata
    start_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), nullable=False))
    duration: int = Field(sa_column=Column(Integer, nullable=False))
    avg_rank_tier: int = Field(sa_column=Column(Integer, nullable=False))
    num_rank_tier: int = Field(sa_column=Column(Integer, nullable=False))
    radiant_win: bool = Field(sa_column=Column(Boolean, nullable=False))

    # Hero IDs (Radiant 0..4, Dire 128..132)
    slot_0_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_1_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_2_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_3_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_4_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_128_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_129_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_130_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_131_hero_id: int = Field(sa_column=Column(Integer, nullable=False))
    slot_132_hero_id: int = Field(sa_column=Column(Integer, nullable=False))

    __table_args__ = (
        Index("ix_public_matches_start_time", "start_time"),
    )
