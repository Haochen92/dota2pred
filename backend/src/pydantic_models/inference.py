from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class PerformanceMetrics(BaseModel):
    accuracy: float = 0.0
    f1_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    
class VersionMetaData(BaseModel):
    changes: List[str] = []
    performance_metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    
class ModelMetaData(BaseModel):
    name: str
    version: str
    trained_date: datetime
    feature_columns = List[str]
    previous_version : str = ""
    version_metadata: VersionMetaData = Field(default_factory=VersionMetaData)
    
class ModelPrediction(BaseModel):
    prediction: List[int]
    probability: Optional[List[float]]