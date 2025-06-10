from sqlmodel import SQLModel, Field
from .schema import LeagueItem

class LeagueTable(SQLModel, LeagueItem, table=True): # type: ignore
    """Database table for league data.
    
    Inherits from LeagueItem with database-specific overrides.
    
    Attributes:
        leagueid: Primary key league identifier (int)
    """
    # overrides LeagueItem
    leagueid: int = Field(primary_key=True)