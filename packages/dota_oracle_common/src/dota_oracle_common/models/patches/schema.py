from datetime import datetime
from pydantic import BaseModel, RootModel, Field, field_validator
from typing import List, Any
from dota_oracle_common.utils.time_utils import to_utc_datetime_object


class DotaPatch(BaseModel):
    """Dota patch data model with automatic datetime conversion.

    Attributes:
        name: Patch version identifier (e.g., "7.35")
        id: Unique patch identifier
        start_time: UTC datetime when patch became active, parsed from API 'date' field
    """

    name: str
    id: int
    start_time: datetime = Field(alias="date")

    @field_validator("start_time", mode="before")
    @classmethod
    def parse_start_time(cls, v: Any) -> datetime:
        """Convert date field to UTC datetime using standardized time parsing."""
        return to_utc_datetime_object(v)

    class Config:
        populate_by_name = True


class DotaPatchAPIResponse(RootModel[List[DotaPatch]]):
    """API response model for patch data.

    Attributes:
        root: List of patch data (List[DotaPatch])
    """

    root: List[DotaPatch]
