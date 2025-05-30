from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory import Use
from datetime import datetime, timezone
from dota_oracle.data_repository.schemas import (
    PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable, # Histories
    TeamFeaturesTable, PlayerHeroFeatureTable, HeroFeaturesTable, # Features
    MatchPredictionTable, # inference
    MatchOutcomeTable, MatchTable, # Matches
    HeroDataTable # herodata
)

from dota_oracle.pydantic_models.match import Match as MatchPydantic


'''
Features Tables
'''
class TeamFeaturesTableFactory(ModelFactory[TeamFeaturesTable]):
    pass

class PlayerHeroFeatureTableFactory(ModelFactory[PlayerHeroFeatureTable]):
    pass

class HeroFeaturesTableFactory(ModelFactory[HeroFeaturesTable]):
    pass


'''
Histories Tables
'''
class PlayerHeroHistoryTableFactory(ModelFactory[PlayerHeroHistoryTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass

class TeamHistoryTableFactory(ModelFactory[TeamHistoryTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass

class TeamMatchupHistoryTableFactory(ModelFactory[TeamMatchupHistoryTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass


'''
Inference Tables
'''
class MatchPredictionTableFactory(ModelFactory[MatchPredictionTable]):
    prediction_date = Use(lambda: datetime.now(timezone.utc))
    pass


'''
Matches Tables
'''
class MatchOutcomeTableFactory(ModelFactory[MatchOutcomeTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass

class MatchTableFactory(ModelFactory[MatchTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass

class MatchPydanticFactory(ModelFactory[MatchPydantic]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass


'''
Hero Data Tables
'''
class HeroDataTableFactory(ModelFactory[HeroDataTable]):
    pass