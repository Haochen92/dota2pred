from typing import Optional 
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, String, TIMESTAMP, Boolean, Integer
from datetime import datetime

class TeamHistoryTable(SQLModel, table=True):
    __tablename__ = 'team_histories' # type: ignore
    
    # Composite Primary Key
    team_name: str = Field(
        sa_column=Column(String, primary_key=True) 
    )
    match_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True) 
    )
    
    win: bool = Field(default=None, sa_column=Column(Boolean, nullable=False)) 
    
    start_time: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=False)
    )

class TeamMatchupHistoryTable(SQLModel, table=True):
    __tablename__ = 'team_matchup_histories' # type: ignore
    
    team1_name: str = Field(
        sa_column=Column(String, primary_key=True)
    )
    team2_name: str = Field(
        sa_column=Column(String, primary_key=True)
    )
    match_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True)
    )
    
    win: bool = Field(default=None, sa_column=Column(Boolean, nullable=False))
    
    start_time: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=False)
    )

class PlayerHeroHistoryTable(SQLModel, table=True):
    __tablename__ = 'player_hero_histories' #type: ignore
    
    # Composite Primary Key
    account_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True) 
    )
    hero_id: int = Field(
        sa_column=Column(Integer, primary_key=True) 
    )
    match_id: int = Field( 
        sa_column=Column(BigInteger, primary_key=True)
    )
    
    win: bool = Field(default=None, sa_column=Column(Boolean, nullable=False))
    
    start_time: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=False)
    )
