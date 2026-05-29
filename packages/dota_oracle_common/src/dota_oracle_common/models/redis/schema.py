from pydantic import BaseModel, field_serializer, Field, model_validator
from enum import Enum
from datetime import datetime, timezone
from typing import Any, TypeVar, Generic, List, Dict
from dota_oracle_common.models.match.base import Match
from dota_oracle_common.models.features.schema import TeamFeatures, HeroFeatures, PlayerHeroFeature


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

    match_details: Match


class PredictionPayload(BaseModel):
    """
    Payload FROM Feature Engineering stage TO Prediction stage.
    Contains the fully processed features ready for the model.
    """

    hero_features: HeroFeatures
    team_features: TeamFeatures
    player_hero_features: PlayerHeroFeature


class CompletionPayload(BaseModel):
    """
    Payload FROM Prediction stage TO Completion stage.
    Contains the model's prediction output.
    """

    match_id: int
    radiant_win: bool


class CompletedMatchPayload(BaseModel):
    """
    Payload for matches which has been completed with actual outcome
    """

    match_outcome: bool


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
    retry_count: int = 0

    @field_serializer("failure_timestamp")
    def serialize_timestamp(self, dt: datetime, _info: Any) -> str:
        return dt.isoformat()


# --- Pydantic Parsers for XREADGROUP Response. To do: in future refactoring


class RedisStreamMessage(BaseModel, Generic[PayloadModel]):
    """
    Represents a single raw message from a Redis Stream.
    Its primary job is to parse the (id, data_dict) tuple and construct
    a high-level ConsumedEvent object.
    """

    id: str = Field(description="The unique ID of the stream message (e.g., '1677694800000-0').")

    # This field holds your fully parsed, high-level event object.
    event: ConsumedEvent[PayloadModel]

    @model_validator(mode="before")
    @classmethod
    def assemble_consumed_event(cls, data: Any) -> Dict[str, Any]:
        """
        Validator to transform the raw (id, dict) tuple from Redis
        into a dictionary that Pydantic can use to build this model.

        """
        if not isinstance(data, tuple) or len(data) != 2:
            raise ValueError("RedisStreamMessage must be created from an (id, data_dict) tuple.")

        event_id = data[0]
        event_data_dict = data[1]

        assembled_event = {**event_data_dict, "event_id": event_id}

        # Return the dictionary in the shape of this model's fields.
        return {"id": event_id, "event": assembled_event}


# 2. The model for a batch of messages from one stream: ('stream_name', [messages...])
class RedisStreamBatch(BaseModel, Generic[PayloadModel]):
    """
    Represents the complete batch of messages returned for a single stream.
    """

    stream_name: str
    messages: List[RedisStreamMessage[PayloadModel]]

    @model_validator(mode="before")
    @classmethod
    def parse_from_redis_tuple(cls, data: Any) -> Dict[str, Any]:
        """Validates and parses the ('stream_name', [messages...]) tuple."""
        if isinstance(data, tuple) and len(data) == 2:
            return {"stream_name": data[0], "messages": data[1]}
        if isinstance(data, dict):  # For testing/factory support
            return data
        raise ValueError("RedisStreamBatch must be created from a (stream_name, messages_list) tuple or a dict")


# 3. The top-level model for the entire response: [batch1, batch2, ...]
class XReadGroupResponse(BaseModel, Generic[PayloadModel]):
    """
    The top-level model representing the entire raw response from XREADGROUP.
    Wraps the list of batches in a standard `BaseModel` for readability.
    """

    root: List[RedisStreamBatch[PayloadModel]]
