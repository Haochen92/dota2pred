from polyfactory.factories.pydantic_factory import ModelFactory
from dota_oracle.models.redis.schema import (
    StreamMatchEventData, MatchStatusValue,
    FailureRecord
)
from polyfactory.pytest_plugin import register_fixture

@register_fixture
class StreamMatchEventDataFactory(ModelFactory[StreamMatchEventData]):
    pass

@register_fixture
class MatchStatusValueFactory(ModelFactory[MatchStatusValue]):
    pass

@register_fixture
class FailureRecordFactory(ModelFactory[FailureRecord]):
    pass




