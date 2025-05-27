from polyfactory.factories.pydantic_factory import ModelFactory
from dota_oracle.data_repository.history_repository import (
    PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable
)

class PlayerHeroHistoryTableFactory(ModelFactory[PlayerHeroHistoryTable]):
    pass

class TeamHistoryTableFactory(ModelFactory[TeamHistoryTable]):
    pass

class TeamMatchupHistoryTableFactory(ModelFactory[TeamMatchupHistoryTable]):
    pass