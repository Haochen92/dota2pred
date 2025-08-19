from polyfactory.factories.pydantic_factory import ModelFactory
from polyfactory import Use
from datetime import datetime, timezone
from polyfactory.pytest_plugin import register_fixture

# import tables

from dota_oracle_common.models.match import MatchOutcomeTable, MatchTable
from dota_oracle_common.models.features import PlayerHeroFeatureTable, TeamFeaturesTable, HeroFeaturesTable
from dota_oracle_common.models.inference import MatchPredictionTable
from dota_oracle_common.models.heroes import HeroDataTable
from dota_oracle_common.models.histories import PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable
from dota_oracle_common.models.patches import PatchTable


from dota_oracle_common.models.match import Match as MatchPydantic


"""
Features Tables
"""


@register_fixture
class TeamFeaturesTableFactory(ModelFactory[TeamFeaturesTable]):
    pass


@register_fixture
class PlayerHeroFeatureTableFactory(ModelFactory[PlayerHeroFeatureTable]):
    pass


@register_fixture
class HeroFeaturesTableFactory(ModelFactory[HeroFeaturesTable]):
    pass


"""
Histories Tables
"""


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


"""
Inference Tables
"""


@register_fixture
class MatchPredictionTableFactory(ModelFactory[MatchPredictionTable]):
    prediction_date = Use(lambda: datetime.now(timezone.utc))
    pass


"""
Matches Tables
"""


@register_fixture
class MatchOutcomeTableFactory(ModelFactory[MatchOutcomeTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass


@register_fixture
class MatchTableFactory(ModelFactory[MatchTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    duration = Use(lambda: 1800.0)  # 30 minutes in seconds

    @classmethod
    def build(cls, **kwargs):
        """
        Custom build method to generate 10 unique hero IDs.
        """
        import random

        # A list of all the slot attribute names we need to populate
        hero_slot_names = [
            "slot_0_hero_id",
            "slot_1_hero_id",
            "slot_2_hero_id",
            "slot_3_hero_id",
            "slot_4_hero_id",
            "slot_128_hero_id",
            "slot_129_hero_id",
            "slot_130_hero_id",
            "slot_131_hero_id",
            "slot_132_hero_id",
        ]

        # Check if the user has manually provided any hero IDs. If they have,
        # we respect their input and don't generate our own.
        if not any(slot_name in kwargs for slot_name in hero_slot_names):

            # 1. Generate 10 unique hero IDs from the range 1-150 (common Dota 2 hero range)
            unique_hero_ids = random.sample(range(1, 151), len(hero_slot_names))

            # 2. Create a dictionary mapping slot names to the unique IDs
            hero_overrides = dict(zip(hero_slot_names, unique_hero_ids))

            # 3. Merge our generated hero IDs with any other kwargs the user passed.
            #    The user's kwargs take precedence if there's a conflict.
            kwargs = {**hero_overrides, **kwargs}

        # 4. Call the original, parent build method with the complete set of arguments.
        return super().build(**kwargs)


@register_fixture
class MatchPydanticFactory(ModelFactory[MatchPydantic]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass


"""
Hero Data Tables
"""


@register_fixture
class HeroDataTableFactory(ModelFactory[HeroDataTable]):
    pass


"""
Patch Tables
"""


@register_fixture
class PatchTableFactory(ModelFactory[PatchTable]):
    start_time = Use(lambda: datetime.now(timezone.utc))
    pass
