from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory import Use
from polyfactory.pytest_plugin import register_fixture

# Import your existing factories
from tests.factories.redis_models_factory import StreamMatchEventDataFactory
from tests.factories.repository_factories import MatchTableFactory


# Model imports for factories
from dota_oracle.models.live_games.schema import OngoingLeagueGame
from dota_oracle.models.inference.schema import ModelPredictionAPIResponse, ModelMetaDataAPIResponse
from dota_oracle.models.pipeline.schema import (
    NewMatchWorkItem,
    FeatureEngineeringWorkItem, 
    PredictionWorkItem,
    CompletionWorkItem
)
from dota_oracle.models.utils import TaskResult, AsyncTask


# ================================
# MODERN POLYFACTORY DEFINITIONS
# ================================

@register_fixture
class OngoingLeagueGameFactory(ModelFactory[OngoingLeagueGame]):
    pass

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