from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory.factories import pydantic_factory
from polyfactory import Use
from polyfactory.pytest_plugin import register_fixture
import random

# Model imports for factories
from dota_oracle_common.models.live_games.schema import OngoingLeagueGame, ScoreBoard, Faction, Player
from dota_oracle_common.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle_common.models.match.schema import MatchesAPIResponse, ProMatchOutcome, PlayerData
from dota_oracle_common.models.pipeline.schema import (
    NewMatchWorkItem,
    FeatureEngineeringWorkItem, 
    PredictionWorkItem,
    CompletionWorkItem
)
from dota_oracle_common.models.utils import TaskResult, AsyncTask


radiant_slot_ids = list(range(5))
dire_slot_ids = list(range(128, 133))

# HELPER FACTORIES DEFINITION
class PlayerFactory(ModelFactory[Player]):
    """
    Player Model factory for live games
    """
    pass

class RadiantFactionFactory(ModelFactory[Faction]):
    players = Use(lambda: [PlayerFactory.build(
        player_slot=i,
        account_id=i + 2000,
        hero_id= (i+1) % 100,
        name=f"Player_{i}"
    ) for i in radiant_slot_ids])

class DireFactionFactory(ModelFactory[Faction]):
    players = Use(lambda: [PlayerFactory.build(
        player_slot=i,
        account_id=i + 2000,
        hero_id= (i+1) % 100,
        name=f"Player_{i}"
    ) for i in dire_slot_ids])
    
class ScoreboardFactory(ModelFactory[ScoreBoard]):
    duration = Use(lambda: random.uniform(1,100))
    radiant: RadiantFactionFactory
    dire: DireFactionFactory
    
class PlayerDataFactory(ModelFactory[PlayerData]):
    pass

# ================================
# POLYFACTORY FIXTURES DEFINITIONS
# ================================


@register_fixture
class OngoingLeagueGameFactory(ModelFactory[OngoingLeagueGame]):
    scoreboard = ScoreboardFactory

@register_fixture
class MatchesAPIResponseFactory(ModelFactory[MatchesAPIResponse]):
    players = Use(lambda: [PlayerDataFactory.build(
        player_slot=j,
        account_id=j+2000,
        hero_id=(j+1) % 100,
        name=f"Player_{j}"
    ) for j in radiant_slot_ids + dire_slot_ids])

@register_fixture
class ModelPredictionAPIResponseFactory(ModelFactory[ModelPredictionAPIResponse]):
    prediction = Use(lambda: [1])

@register_fixture
class ModelMetaDataAPIResponseFactory(ModelFactory[ModelMetaDataAPIResponse]):
    pass

@register_fixture
class NewMatchWorkItemFactory(ModelFactory[NewMatchWorkItem]):
    pass

@register_fixture
class FeatureEngineeringWorkItemFactory(ModelFactory[FeatureEngineeringWorkItem]):
    pass

@register_fixture
class PredictionWorkItemFactory(ModelFactory[PredictionWorkItem]):
    pass

@register_fixture
class CompletionWorkItemFactory(ModelFactory[CompletionWorkItem]):
    outcome = Use(lambda: True)
    
@register_fixture
class TaskResultFactory(ModelFactory[TaskResult]):
    pass

@register_fixture
class AsyncTaskFactory(ModelFactory[AsyncTask]):
    pass