from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, String, TIMESTAMP, Boolean, Integer
from datetime import datetime


class TeamHistoryTable(SQLModel, table=True):
    """Database table for team match history.

    Attributes:
        team_name: Team name (str, primary key)
        match_id: Match identifier (BigInteger, primary key)
        win: Whether team won (bool)
        start_time: Match start with timezone (TIMESTAMP)
    """

    __tablename__ = "team_histories"

    # Composite Primary Key
    team_name: str = Field(sa_column=Column(String, primary_key=True))
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True))

    win: bool = Field(default=None, sa_column=Column(Boolean, nullable=False))

    start_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=False))


class TeamMatchupHistoryTable(SQLModel, table=True):
    """Database table for team vs team matchup history.

    Attributes:
        team1_name, team2_name: Team names (str, primary key)
        match_id: Match identifier (BigInteger, primary key)
        win: Whether team1 won (bool)
        start_time: Match start with timezone (TIMESTAMP)
    """

    __tablename__ = "team_matchup_histories"

    team1_name: str = Field(sa_column=Column(String, primary_key=True))
    team2_name: str = Field(sa_column=Column(String, primary_key=True))
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True))

    win: bool = Field(default=None, sa_column=Column(Boolean, nullable=False))

    start_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=False))


class PlayerHeroHistoryTable(SQLModel, table=True):
    """Database table for player-hero combination history.

    Attributes:
        account_id: Player account ID (BigInteger, primary key)
        hero_id: Hero identifier (Integer, primary key)
        match_id: Match identifier (BigInteger, primary key)
        win: Whether player won with this hero (bool)
        start_time: Match start with timezone (TIMESTAMP)
    """

    __tablename__ = "player_hero_histories"

    # Composite Primary Key
    account_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    hero_id: int = Field(sa_column=Column(Integer, primary_key=True))
    match_id: int = Field(sa_column=Column(BigInteger, primary_key=True))

    win: bool = Field(default=None, sa_column=Column(Boolean, nullable=False))

    start_time: datetime = Field(sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=False))
