from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture
from dota_oracle_common.models.api import LiveStateUpdateRequest
from dota_oracle_common.models.pagination import PaginationFilters, PaginatedMatchResponse


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


@register_fixture
class PaginationFiltersFactory(ModelFactory[PaginationFilters]):
    """
    Model Factory for PaginationFilters
    """

    pass


@register_fixture
class PaginatedMatchResponseFactory(ModelFactory[PaginatedMatchResponse]):
    """
    Model Factory for PaginatedMatchResponse
    """

    pass
