from polyfactory.factories.pydantic_factory import ModelFactory
from dota_oracle.pydantic_models.redis_models import (
    StreamMatchEventData, MatchStatusValue,
    FailureRecord
)

class StreamMatchEventDataFactory(ModelFactory[StreamMatchEventData]):
    pass

class MatchStatusValueFactory(ModelFactory[MatchStatusValue]):
    pass

class FailureRecordFactory(ModelFactory[FailureRecord]):
    pass




