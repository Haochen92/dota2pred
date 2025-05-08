from typing import Optional 
from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, String, TIMESTAMP, Boolean, Integer
from datetime import datetime

class TeamHistoryTable(SQLModel, table=True):
    __tablename__ = 'team_histories'
    
    # Composite Primary Key
    team_name: str = Field(
        sa_column=Column(String, primary_key=True) 
    )
    match_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True) 
    )
    
    win: Optional[bool] = Field(default=None, sa_column=Column(Boolean, nullable=True)) 
    
    start_time: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=True)
    )

class TeamMatchupHistoryTable(SQLModel, table=True):
    __tablename__ = 'team_matchup_histories'
    
    team1_name: str = Field(
        sa_column=Column(String, primary_key=True)
    )
    team2_name: str = Field(
        sa_column=Column(String, primary_key=True)
    )
    match_id: int = Field(
        sa_column=Column(BigInteger, primary_key=True)
    )
    
    win: Optional[bool] = Field(default=None, sa_column=Column(Boolean, nullable=True))
    
    start_time: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=True)
    )

class PlayerHeroHistoryTable(SQLModel, table=True):
    __tablename__ = 'player_hero_histories'
    
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
    
    win: Optional[bool] = Field(default=None, sa_column=Column(Boolean, nullable=True))
    
    start_time: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=True)
    )
