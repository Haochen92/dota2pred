from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, JSON, String
from typing import List, Optional

class TeamHistories(SQLModel, table=True):
    __tablename__ = 'team_histories'
    
    team_name: str = Field(sa_type=String, primary_key=True)
    
    matches: List[dict] = Field(sa_column=Column(JSON))
    last_updated: Optional[int] = Field(default=None, sa_column=Column("last_updated", BigInteger))
    
class TeamMatchupHistories(SQLModel, table=True):
    __tablename__ = 'team_matchup_histories'
    
    team1_name: str = Field(primary_key=True, sa_type=String)
    team2_name: str = Field(primary_key=True, sa_type=String)
    # primary key is composite of above 2 keys
    
    matches: List[dict] = Field(sa_column=Column(JSON))
    last_updated: Optional[int] = Field(default=None, sa_column=Column("last_updated", BigInteger))

class PlayerHeroHistories(SQLModel, table=True):
    __tablename__ = 'player_hero_histories'
    
    account_id: int = Field(sa_column=Column("account_id", BigInteger, primary_key=True))
    hero_name: str = Field(primary_key=True, sa_type=String)
    # primary key is composite of above 2 keys
    
    matches: List[dict] = Field(sa_column=Column(JSON))
    last_updated: Optional[int] = Field(default=None, sa_column=Column("last_updated", BigInteger))