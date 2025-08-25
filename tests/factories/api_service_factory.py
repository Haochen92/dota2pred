from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.pytest_plugin import register_fixture
from dota_oracle_common.models.api import LiveStateUpdateRequest, PublicMatchPredictionRequest
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


@register_fixture
class PublicMatchPredictionRequestFactory(ModelFactory[PublicMatchPredictionRequest]):
    """
    Model Factory for PublicMatchPredictionRequest

    ***
    class PublicMatchPredictionRequest(BaseModel):
        radiant_hero_id_1: int
        radiant_hero_id_2: int
        radiant_hero_id_3: int
        radiant_hero_id_4: int
        radiant_hero_id_5: int
        dire_hero_id_1: int
        dire_hero_id_2: int
        dire_hero_id_3: int
        dire_hero_id_4: int
        dire_hero_id_5: int
    ***
    """

    pass
