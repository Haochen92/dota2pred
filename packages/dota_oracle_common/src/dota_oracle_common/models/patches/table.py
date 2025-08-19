from sqlmodel import Field, SQLModel
from sqlalchemy import Column, TIMESTAMP, Integer, String
from datetime import datetime
from typing import Optional


class PatchTable(SQLModel, table=True):
    """Database table for patch data.

    Attributes:
        id: Primary key patch identifier (int)
        patch_number: Patch version string (str)
        start_time: Patch release datetime with timezone support (datetime)
        end_time: Patch end datetime (when next patch starts), None for latest patch (Optional[datetime])
    """

    __tablename__ = "patches"

    id: int = Field(sa_column=Column("id", Integer, primary_key=True))
    patch_number: str = Field(sa_column=Column("patch_number", String(50), nullable=False, unique=True, index=True))
    start_time: datetime = Field(sa_column=Column("start_time", TIMESTAMP(timezone=True), nullable=False))
    end_time: Optional[datetime] = Field(sa_column=Column("end_time", TIMESTAMP(timezone=True), nullable=True))
