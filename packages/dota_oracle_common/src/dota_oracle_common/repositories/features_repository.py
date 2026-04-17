from sqlalchemy.ext.asyncio import AsyncSession
from .base_repository import BaseRepository, T
from ..utils.set_logging import get_logger
from typing import Optional, List, Type

from dota_oracle_common.models.features import TeamFeaturesTable, HeroFeaturesTable, PlayerHeroFeatureTable
from dota_oracle_common.models.match import MatchTable, MatchOutcomeTable
from sqlalchemy import or_
from sqlmodel import select
from datetime import datetime

logger = get_logger(__name__)


class FeaturesRepository(BaseRepository):

    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.session = session

    """
    Repository class for handling database operations related to
    match features (Hero, Team, Player-Hero).
    Uses asynchronous SQLAlchemy Core and targets PostgreSQL.
    Returns SQLModel instances or lists thereof.
    """

    async def store_features(
        self,
        feature_instances: List[T],
        table_class: Type[T],
    ) -> None:
        """
        Upserts a list of SQLModel feature instances into the specified table.

        Args:
            feature_instances: List of SQLModel instances to upsert (e.g., HeroFeaturesTable, TeamFeaturesTable).
            table_class: The SQLModel table class representing the target table.
        """
        if not feature_instances:
            logger.warning(f"Received empty list for storing features in {table_class.__name__}. Skipping.")
            return
        try:
            await self._upsert_data(
                model_class=table_class,
                instances=feature_instances,
            )
        except Exception as e:
            raise e

    async def get_features(
        self,
        *,
        table_class: Type[T],
        match_ids: Optional[List[int]] = None,
        limit: Optional[int] = None,
    ) -> List[T]:
        """
        Fetches a list of feature rows from the specified table.

        Args:
            table_class: The SQLModel table class (e.g., HeroFeaturesTable).
            match_ids: Optional list of primary key match ids. If none provided, fetch all the data.
            limit: Optional maximum number of rows to return.

        Returns:
            A list of SQLModel instances; empty list if none found.
        """
        try:
            feature_instance_list = await self._get_data(model_class=table_class, id_filters=match_ids, limit=limit)

            if not feature_instance_list:
                debug_message = f"No results found for table {table_class.__name__}, " f"inputs: {match_ids}"
                logger.debug(debug_message)
                return []

            logger.info(f"Found {len(feature_instance_list)} results")
            return feature_instance_list
        except Exception as e:
            raise e

    async def get_team_features(
        self, match_ids: Optional[List[int]] = None, limit: Optional[int] = None
    ) -> List[TeamFeaturesTable]:
        return await self.get_features(table_class=TeamFeaturesTable, match_ids=match_ids, limit=limit)

    async def get_hero_features(
        self, match_ids: Optional[List[int]] = None, limit: Optional[int] = None
    ) -> List[HeroFeaturesTable]:
        return await self.get_features(table_class=HeroFeaturesTable, match_ids=match_ids, limit=limit)

    async def get_player_hero_features(
        self, match_ids: Optional[List[int]] = None, limit: Optional[int] = None
    ) -> List[PlayerHeroFeatureTable]:
        return await self.get_features(table_class=PlayerHeroFeatureTable, match_ids=match_ids, limit=limit)

    async def get_earliest_missing_features_time(self) -> Optional[datetime]:
        """
        Find the earliest completed match (has outcome) that is missing any of the feature rows
        (team_features OR hero_features OR player_hero_features).
        Returns its start_time or None if none missing.
        """
        try:
            stmt = (
                select(MatchTable.start_time)
                .select_from(MatchTable)
                .join(MatchOutcomeTable, MatchOutcomeTable.match_id == MatchTable.match_id)
                .outerjoin(TeamFeaturesTable, TeamFeaturesTable.match_id == MatchTable.match_id)
                .outerjoin(HeroFeaturesTable, HeroFeaturesTable.match_id == MatchTable.match_id)
                .outerjoin(PlayerHeroFeatureTable, PlayerHeroFeatureTable.match_id == MatchTable.match_id)
                .where(
                    or_(
                        TeamFeaturesTable.match_id.is_(None),
                        HeroFeaturesTable.match_id.is_(None),
                        PlayerHeroFeatureTable.match_id.is_(None),
                    )
                )
                .order_by(MatchTable.start_time.asc())
                .limit(1)
            )
            res = await self.session.execute(stmt)
            row = res.first()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Error finding earliest missing features time: {e}", exc_info=True)
            raise
