from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture
from dota_oracle_common.models.api import LiveStateUpdateRequest


@register_fixture
class LiveStateUpdateRequestFactory(ModelFactory[LiveStateUpdateRequest]):
    """
    Model Factory for LiveStateUpdateRequest

    ***
    class LiveStateUpdateRequest(BaseModel):
        live_matches: List[MatchNotifcationAPIPayload]
    ***
    """

    pass
