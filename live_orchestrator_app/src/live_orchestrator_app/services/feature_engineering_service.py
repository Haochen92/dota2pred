from dota_oracle_pipeline.feature_engineering import TeamFeatureCreator, PlayerHeroFeaturesCreator, HeroesFeatureCreator
from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.models.match import MatchTable
from dota_oracle_common.models.features import HeroFeaturesTable, TeamFeaturesTable, PlayerHeroFeatureTable
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.utils.async_utils import TaskRunner
from dota_oracle_common.models.utils import AsyncTask
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

logger = get_logger(__name__)


class FeatureEngineeringService:

    def __init__(
        self,
        team_feature_creator: TeamFeatureCreator,
        player_hero_feature_creator: PlayerHeroFeaturesCreator,
    ):
        self.team_feature_creator = team_feature_creator
        self.player_hero_feature_creator = player_hero_feature_creator

    async def create_and_store_features(self, match_instance: MatchTable, session: AsyncSession) -> None:
        if not match_instance:
            logger.warning("no match_instances for data creation")
            return None

        try:
            hero_features = HeroesFeatureCreator.create_hero_features([match_instance])
            team_features = await self.team_feature_creator.create_team_features(session, [match_instance])
            player_hero_features = await self.player_hero_feature_creator.create_player_hero_features(
                session, [match_instance]
            )
        except Exception as e:
            logger.error(f"Error creating features {e}", exc_info=True)
            raise e

        if not hero_features or not team_features or not player_hero_features:
            error_msg = f"""
                Incomplete features, raising 
                expected hero_features , got {hero_features}
                expected team_features , got {team_features}
                expected player_hero_features , got {player_hero_features}
            """
            raise ValueError(error_msg)

        # Create repository with the provided session
        features_repository = FeaturesRepository(session=session)

        # Create AsyncTask objects for TaskGroup execution
        storage_tasks: List[AsyncTask] = [
            AsyncTask(
                key="hero_features_storage",
                coro=features_repository.store_features(feature_instances=hero_features, table_class=HeroFeaturesTable),
            ),
            AsyncTask(
                key="team_features_storage",
                coro=features_repository.store_features(feature_instances=team_features, table_class=TeamFeaturesTable),
            ),
            AsyncTask(
                key="player_hero_features_storage",
                coro=features_repository.store_features(
                    feature_instances=player_hero_features, table_class=PlayerHeroFeatureTable
                ),
            ),
        ]

        try:
            # Use TaskGroup for concurrent execution (requires Python 3.11+)
            await TaskRunner.run_as_group(storage_tasks)
            logger.debug(f"Successfully stored all features for match {match_instance.match_id}")
        except Exception as e:
            logger.error(f"Error storing features {e}", exc_info=True)
            raise e
