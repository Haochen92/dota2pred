from pydantic import BaseModel, field_serializer
from enum import Enum
from datetime import datetime


# Enums
class MatchProcessingStatus(str, Enum):
    """
    Represents the possible statuses of a match during processing.
    The string value is what's stored in Redis.
    """
    NEW = "new"
    PENDING_PREDICTION = "pending_prediction"
    PENDING_COMPLETION = "pending_completion"



# Pyndantic Models
class StreamMatchEventData(BaseModel):
    """
    Data model for messages in the match processing streams.
    e.g., {'match_id': '12345', 'timestamp': isoformat}
    """
    match_id: int 
    timestamp: datetime
    
    @field_serializer('timestamp')
    def serialize_timestamp(self, dt: datetime, _info):
        return dt.isoformat()

    
class MatchStatusValue(BaseModel):
    """
    Data model for the value stored in the MATCH_STATUS:{match_id} hash.
    e.g., {'status': 'new'}
    """
    status: MatchProcessingStatus



class FailureRecord(BaseModel):
    """
    Data model for the information stored in DLQ hashes when an event fails.
    This is serialized to JSON before being stored in the hash.
    """
    original_group: str
    original_event_id: str
    original_stream: str
    original_data: StreamMatchEventData
    error_type: str
    error_message: str
    failure_timestamp: datetime

    
