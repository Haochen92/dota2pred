from polyfactory.factories.pydantic_factory import ModelFactory
from dota_oracle.data_repository.schemas import (
    PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable, # Histories
    TeamFeaturesTable, PlayerHeroFeatureTable, HeroFeaturesTable, # Features
    MatchPredictionTable, # inference
    MatchOutcomeTable, MatchTable, # Matches
    HeroDataTable # herodata
)


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
    pass

class TeamHistoryTableFactory(ModelFactory[TeamHistoryTable]):
    pass

class TeamMatchupHistoryTableFactory(ModelFactory[TeamMatchupHistoryTable]):
    pass


'''
Inference Tables
'''
class MatchPredictionTableFactory(ModelFactory[MatchPredictionTable]):
    pass


'''
Matches Tables
'''
class MatchOutcomeTableFactory(ModelFactory[MatchOutcomeTable]):
    pass

class MatchTableFactory(ModelFactory[MatchTable]):
    pass


'''
Hero Data Tables
'''
class HeroDataTableFactory(ModelFactory[HeroDataTable]):
    pass