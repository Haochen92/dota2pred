from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory import Use
from datetime import datetime, timezone
from polyfactory.pytest_plugin import register_fixture

# import tables

from dota_oracle_common.models.match import (
    MatchOutcomeTable, MatchTable
)
from dota_oracle_common.models.features import (
    PlayerHeroFeatureTable, TeamFeaturesTable, HeroFeaturesTable
)
from dota_oracle_common.models.inference import (
    MatchPredictionTable
)
from dota_oracle_common.models.heroes import (
    HeroDataTable
)
from dota_oracle_common.models.histories import (
    PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable
)



from dota_oracle_common.models.match import Match as MatchPydantic


'''
Features Tables
'''
@register_fixture
class TeamFeaturesTableFactory(ModelFactory[TeamFeaturesTable]):
    pass
@register_fixture
class PlayerHeroFeatureTableFactory(ModelFactory[PlayerHeroFeatureTable]):
    pass
@register_fixture
class HeroFeaturesTableFactory(ModelFactory[HeroFeaturesTable]):
    pass


'''
Histories Tables
'''
@register_fixture
class PlayerHeroHistoryTableFactory(ModelFactory[PlayerHeroHistoryTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass
@register_fixture
class TeamHistoryTableFactory(ModelFactory[TeamHistoryTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass
@register_fixture
class TeamMatchupHistoryTableFactory(ModelFactory[TeamMatchupHistoryTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass


'''
Inference Tables
'''
@register_fixture
class MatchPredictionTableFactory(ModelFactory[MatchPredictionTable]):
    prediction_date = Use(lambda: datetime.now(timezone.utc))
    pass


'''
Matches Tables
'''
@register_fixture
class MatchOutcomeTableFactory(ModelFactory[MatchOutcomeTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass
@register_fixture
class MatchTableFactory(ModelFactory[MatchTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass
@register_fixture
class MatchPydanticFactory(ModelFactory[MatchPydantic]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass


'''
Hero Data Tables
'''
@register_fixture
class HeroDataTableFactory(ModelFactory[HeroDataTable]):
    pass