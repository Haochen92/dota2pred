from sqlmodel import SQLModel, Field, Relationship
from .schema import LeagueItem
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..match.table import MatchTable


class LeagueTable(SQLModel, LeagueItem, table=True):
    """Database table for league data.

    Inherits from LeagueItem with database-specific overrides.

    Attributes:
        Inherited:
        tier: League tier/level (Optional[str])
        name: League display name (Optional[str])

        Overrides:
        leagueid: Primary key league identifier (int)

        Relationships:
        matches: List of associated matches (List[MatchTable])
    """

    # overrides LeagueItem
    leagueid: int = Field(primary_key=True)

    # Foreign Key Relationships
    matches: list["MatchTable"] = Relationship(back_populates="league_data")  # type: ignore
