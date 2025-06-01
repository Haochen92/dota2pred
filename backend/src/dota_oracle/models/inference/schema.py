from pydantic import BaseModel, Field
from sqlmodel import SQLModel
from typing import List, Optional
from datetime import datetime

# API responses
class PerformanceMetrics(BaseModel):
    accuracy: float = 0.0
    f1_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    
class VersionMetaData(BaseModel):
    changes: List[str] = []
    performance_metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    
class ModelMetaDataAPIResponse(BaseModel):
    name: str
    version: str
    trained_date: datetime
    feature_columns: List[str]
    previous_version : str = ""
    version_metadata: VersionMetaData = Field(default_factory=VersionMetaData)
    
class ModelPredictionAPIResponse(BaseModel):
    prediction: List[int]
    probability: Optional[List[float]]

   

# DTO
class MatchPrediction(SQLModel):
    match_id: int 
    predictor_name: str
    
    prediction: Optional[bool]
    prediction_probability: Optional[float]
    
    predictor_version: Optional[str]
    prediction_date: Optional[datetime] 

