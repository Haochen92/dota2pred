from pydantic import BaseModel, Field
from sqlmodel import SQLModel
from typing import List, Optional
from datetime import datetime


# API responses
class PerformanceMetrics(BaseModel):
    """Model performance metrics container.

    Attributes:
        accuracy: Classification accuracy (float)
        f1_score: F1 score metric (float)
        precision: Precision metric (float)
        recall: Recall metric (float)
    """

    accuracy: float = 0.0
    f1_score: float = 0.0
    precision: float = 0.0
    recall: float = 0.0


class VersionMetaData(BaseModel):
    """Version metadata for model releases.

    Attributes:
        changes: List of changes in this version (List[str])
        performance_metrics: Performance metrics for this version (PerformanceMetrics)
    """

    changes: List[str] = []
    performance_metrics: PerformanceMetrics = Field(default_factory=PerformanceMetrics)
    feature_columns: List[str] = []


class ModelMetaData(BaseModel):
    """Model Metadata Schema.

    Attributes:
        name: Model name (str)
        version: Current version (str)
        trained_date: Model training date (datetime)
        feature_columns: List of feature column names (List[str])
        previous_version: Previous model version (str)
        version_metadata: Version-specific metadata (VersionMetaData)
    """

    name: str
    version: str
    trained_date: datetime
    previous_version: str = ""
    version_metadata: VersionMetaData = Field(default_factory=VersionMetaData)


class ModelMetaDataAPIResponse(ModelMetaData):
    """API response for model metadata information.

    Attributes:
        name: Model name (str)
        version: Current version (str)
        trained_date: Model training date (datetime)
        feature_columns: List of feature column names (List[str])
        previous_version: Previous model version (str)
        version_metadata: Version-specific metadata (VersionMetaData)
    """


class ModelPredictionAPIResponse(BaseModel):
    """API response for model predictions.

    Attributes:
        prediction: Prediction results (List[int])
        probability: Prediction probabilities (Optional[List[float]])
    """

    prediction: List[int]
    probability: Optional[List[float]] = []


# DTO
class MatchPrediction(SQLModel):
    """DTO for match prediction data.

    Attributes:
        match_id: Match identifier (int)
        predictor_name: Name of the predictor model (str)
        prediction: Prediction result (Optional[bool])
        prediction_probability: Confidence score 0-1 (Optional[float])
        predictor_version: Model version used (str)
        prediction_date: When prediction was made (datetime)
    """

    match_id: int
    predictor_name: str

    prediction: Optional[bool]
    prediction_probability: Optional[float] = Field(ge=0.0, le=1.0)

    predictor_version: str = Field(default="v1.0")
    prediction_date: datetime


class PredictionInputPayload(BaseModel):
    input_features: List[List[float]]
