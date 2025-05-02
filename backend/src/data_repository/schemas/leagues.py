from sqlmodel import SQLModel, Field
from pydantic_models.leagues import LeagueItem

class LeagueTable(SQLModel, LeagueItem, table=True):
    # overrides LeagueItem
    league_id: int = Field(primary_key=True)