from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, String

class TeamHistoryTable(SQLModel, table=True):
    __tablename__ = 'team_histories'
    
    team_name: str = Field(sa_type=String, primary_key=True)
    match_id: int = Field(sa_column=Column("match_id", BigInteger, primary_key=True))
    
    win: bool
    start_time: float = Field(index=True)
    
class TeamMatchupHistoryTable(SQLModel, table=True):
    __tablename__ = 'team_matchup_histories'
    
    # composite primary key
    team1_name: str = Field(primary_key=True, sa_type=String)
    team2_name: str = Field(primary_key=True, sa_type=String)
    match_id: int = Field(sa_column=Column("match_id", BigInteger, primary_key=True))
    
    win: bool
    start_time: float = Field(index=True)

class PlayerHeroHistoryTable(SQLModel, table=True):
    __tablename__ = 'player_hero_histories'
    
    # Composite primary key
    account_id: int = Field(sa_column=Column("account_id", BigInteger, primary_key=True))
    hero_id: int = Field(primary_key=True)
    match_id: int = Field(sa_column=Column("match_id", BigInteger, primary_key=True))
    
    win: bool
    start_time: float = Field(index=True)