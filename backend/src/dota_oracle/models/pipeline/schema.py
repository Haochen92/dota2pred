from sqlmodel import SQLModel
from ..redis import StreamMatchEventData

class CompletionWorkItem(SQLModel):
    event_id: str
    event_data: StreamMatchEventData
    outcome: bool