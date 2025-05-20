from sqlmodel import SQLModel, Field
from sqlalchemy import BigInteger, Column, TIMESTAMP
from datetime import datetime
from typing import Optional

class MatchPredictionTable(SQLModel, table=True):
    __tablename__ = 'match_predictions' # type: ignore
    
    # Composite Primary Key
    match_id: int = Field(sa_type=BigInteger, primary_key=True)
    predictor_name: str = Field(primary_key=True, index=True)
    
    prediction: Optional[bool]
    predictor_version: str = Field(default=None)
    prediction_date: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), index=True, nullable=True)
    ) 
    prediction_probability: Optional[float] = Field(default=None)
