from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory import Use
from polyfactory.pytest_plugin import register_fixture

# Model imports for factories
from dota_oracle_common.models.live_games.schema import (
    OngoingLeagueGame,
    OngoingFaction,
    OngoingPlayer,
    Player,
    ScoreBoard,
)
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle_common.models.match.schema import MatchesAPIResponse, PlayerData
from dota_oracle_common.models.utils import TaskResult, AsyncTask
from dota_oracle_common.models.patches.schema import DotaPatch, DotaPatchAPIResponse


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


def _ongoing_scoreboard() -> ScoreBoard[OngoingFaction]:
    """Builds a valid scoreboard with 10 distinct hero_ids (1-10), as a real draft has."""

    def faction(hero_ids: range) -> OngoingFaction:
        return OngoingFaction(
            players=[
                OngoingPlayer(player_slot=slot, account_id=1000 + slot, hero_id=hero)
                for slot, hero in enumerate(hero_ids)
            ]
        )

    return ScoreBoard(duration=0.0, radiant=faction(range(1, 6)), dire=faction(range(6, 11)))


@register_fixture
class OngoingLeagueGameFactory(ModelFactory[OngoingLeagueGame]):
    # OngoingLeagueGame requires 10 distinct heroes; polyfactory's random gt=0 ints collide,
    # so provide a valid draft scoreboard explicitly.
    scoreboard = Use(_ongoing_scoreboard)


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


@register_fixture
class DotaPatchFactory(ModelFactory[DotaPatch]):
    pass


@register_fixture
class DotaPatchAPIResponseFactory(ModelFactory[DotaPatchAPIResponse]):
    pass
