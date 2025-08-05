from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory import Use
from polyfactory.pytest_plugin import register_fixture

# Model imports for factories
from dota_oracle_common.models.live_games.schema import OngoingLeagueGame, Player
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle_common.models.match.schema import MatchesAPIResponse, PlayerData
from dota_oracle_common.models.utils import TaskResult, AsyncTask


# ================================
# POLYFACTORY FIXTURES DEFINITIONS
# ================================
@register_fixture
class PlayerFactory(ModelFactory[Player]):
    """
    Player Model factory for live games
    """

    pass


@register_fixture
class PlayerDataFactory(ModelFactory[PlayerData]):
    """
    Player Model factory for completed games
    """

    pass


@register_fixture
class OngoingLeagueGameFactory(ModelFactory[OngoingLeagueGame]):
    pass


@register_fixture
class MatchesAPIResponseFactory(ModelFactory[MatchesAPIResponse]):
    pass


@register_fixture
class ModelPredictionAPIResponseFactory(ModelFactory[ModelPredictionAPIResponse]):
    prediction = Use(lambda: [1])


@register_fixture
class ModelMetaDataAPIResponseFactory(ModelFactory[ModelMetaDataAPIResponse]):
    pass


@register_fixture
class TaskResultFactory(ModelFactory[TaskResult]):
    pass


@register_fixture
class AsyncTaskFactory(ModelFactory[AsyncTask]):
    pass
