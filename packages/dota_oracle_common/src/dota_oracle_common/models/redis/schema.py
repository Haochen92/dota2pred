from pydantic import BaseModel, field_serializer, Field
from enum import Enum
from datetime import datetime, timezone
from typing import Any, TypeVar, Generic
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.models.features import HeroFeaturesTable, PlayerHeroFeatureTable, TeamFeaturesTable

PayloadModel = TypeVar("PayloadModel", bound=BaseModel)


# Enums
class MatchProcessingStatus(str, Enum):
    """
    Represents the possible statuses of a match during processing.
    The string value is what's stored in Redis.

    # Attributes
    New = "new"
    PENDING_PREDICTION = "pending_prediction"
    PENDING_COMPLETION = "pending_completion"

    """

    NEW = "new"
    PENDING_PREDICTION = "pending_prediction"
    PENDING_COMPLETION = "pending_completion"


class FeatureEngineeringPayload(BaseModel):
    """
    Payload FROM New Match stage TO Feature Engineering stage.
    Contains all the raw data needed to generate features.
    """

    match_details: MatchTable


class PredictionPayload(BaseModel):
    """
    Payload FROM Feature Engineering stage TO Prediction stage.
    Contains the fully processed features ready for the model.
    """

    hero_features: HeroFeaturesTable
    team_features: TeamFeaturesTable
    player_hero_features: PlayerHeroFeatureTable


class CompletionPayload(BaseModel):
    """
    Payload FROM Prediction stage TO Completion stage.
    Contains the model's prediction output.
    """

    match_id: int
    radiant_win: bool


class StreamEvent(BaseModel, Generic[PayloadModel]):
    match_id: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payload: PayloadModel

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime, _info: Any) -> str:
        return dt.isoformat()


class EventToPublish(StreamEvent[PayloadModel]):
    """The data and payload for an event before it is sent to Redis."""

    pass


class ConsumedEvent(StreamEvent[PayloadModel]):
    """An event that has been read from Redis, guaranteed to have an event_id."""

    event_id: str


class MatchStatusValue(BaseModel):
    """
    Data model for the value stored in the MATCH_STATUS:{match_id} hash.
    e.g., {'status': 'new'}
    """

    status: MatchProcessingStatus


class FailureRecord(BaseModel, Generic[PayloadModel]):
    """
    Data model for the information stored in DLQ hashes when an event fails.
    This is serialized to JSON before being stored in the hash.

    Attributes:
        original_group: str (Group from Incoming Stream)
        original_event_id: str (Event_id from Incoming Stream)
        original_stream: str (Incoming Stream)
        original_data: StreamMatchEvent (Event data from Incoming Stream)
        error_type: str
        error_message: str
        failure_timestamp: datetime
    """

    original_group: str
    original_event_id: str
    original_stream: str
    original_data: ConsumedEvent
    error_type: str
    error_message: str
    failure_timestamp: datetime

    @field_serializer("failure_timestamp")
    def serialize_timestamp(self, dt: datetime, _info: Any) -> str:
        return dt.isoformat()
