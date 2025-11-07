from typing import List, Optional, Coroutine
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select, desc

from ..models.histories.table import (
    TeamDecayedStateTable,
    TeamMatchupDecayedStateTable,
    PlayerHeroDecayedStateTable,
    HeroDecayedStateTable,
)
from ..utils.set_logging import get_logger
from .base_repository import BaseRepository

logger = get_logger(__name__)


class HistoryRepository(BaseRepository):
    """
    Repository for accessing and storing a full history of decayed states.
    This enables causally-correct feature generation by time-traveling
    to the state before any given match.

    Follows the Unit of Work pattern - accepts a session that manages transactions.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

    # --- UPSERTERS ---

    async def upsert_team_decayed_states(self, instances: List[TeamDecayedStateTable]) -> None:
        if not instances:
            logger.debug("No TeamDecayedStateTable instances provided for upsert.")
            return
        coro = self._upsert_data(model_class=TeamDecayedStateTable, instances=instances)
        await self._run_and_handle_errors(coro, "upserting TeamDecayedStateTable instances")

    async def upsert_team_matchup_decayed_states(self, instances: List[TeamMatchupDecayedStateTable]) -> None:
        if not instances:
            logger.debug("No TeamMatchupDecayedStateTable instances provided for upsert.")
            return
        coro = self._upsert_data(model_class=TeamMatchupDecayedStateTable, instances=instances)
        await self._run_and_handle_errors(coro, "upserting TeamMatchupDecayedStateTable instances")

    async def upsert_player_hero_decayed_states(self, instances: List[PlayerHeroDecayedStateTable]) -> None:
        if not instances:
            logger.debug("No PlayerHeroDecayedStateTable instances provided for upsert.")
            return
        coro = self._upsert_data(model_class=PlayerHeroDecayedStateTable, instances=instances)
        await self._run_and_handle_errors(coro, "upserting PlayerHeroDecayedStateTable instances")

    async def upsert_hero_decayed_states(self, instances: List[HeroDecayedStateTable]) -> None:
        if not instances:
            logger.debug("No HeroDecayedStateTable instances provided for upsert.")
            return
        coro = self._upsert_data(model_class=HeroDecayedStateTable, instances=instances)
        await self._run_and_handle_errors(coro, "upserting HeroDecayedStateTable instances")

    # --- GETTERS

    async def get_team_state_before(self, team_name: str, before_time: datetime) -> Optional[TeamDecayedStateTable]:
        """Gets the most recent decayed state for a team before a specific time."""
        stmt = (
            select(TeamDecayedStateTable)
            .where(TeamDecayedStateTable.team_name == team_name)
            .where(TeamDecayedStateTable.last_update_time < before_time)
            .order_by(desc(TeamDecayedStateTable.last_update_time))
            .limit(1)
        )
        res = await self._execute_and_handle_errors(
            stmt, f"fetching team decayed state for {team_name} before {before_time}"
        )
        return res.scalars().first()

    async def get_team_state_before_by_id(self, team_id: int, before_time: datetime) -> Optional[TeamDecayedStateTable]:
        """Gets the most recent decayed state for a team (by ID) before a specific time."""
        stmt = (
            select(TeamDecayedStateTable)
            .where(TeamDecayedStateTable.team_id == team_id)
            .where(TeamDecayedStateTable.last_update_time < before_time)
            .order_by(desc(TeamDecayedStateTable.last_update_time))
            .limit(1)
        )
        res = await self._execute_and_handle_errors(
            stmt, f"fetching team decayed state for id={team_id} before {before_time}"
        )
        return res.scalars().first()

    async def get_team_matchup_state_before(
        self, team_one: str, team_two: str, before_time: datetime
    ) -> Optional[TeamMatchupDecayedStateTable]:
        """Gets the most recent decayed state for a matchup before a specific time."""
        t1, t2 = sorted([team_one, team_two])
        stmt = (
            select(TeamMatchupDecayedStateTable)
            .where(
                TeamMatchupDecayedStateTable.team1_name == t1,
                TeamMatchupDecayedStateTable.team2_name == t2,
            )
            .where(TeamMatchupDecayedStateTable.last_update_time < before_time)
            .order_by(desc(TeamMatchupDecayedStateTable.last_update_time))
            .limit(1)
        )
        res = await self._execute_and_handle_errors(
            stmt, f"fetching matchup decayed state for {t1} vs {t2} before {before_time}"
        )
        return res.scalars().first()

    async def get_team_matchup_state_before_by_id(
        self, team1_id: int, team2_id: int, before_time: datetime
    ) -> Optional[TeamMatchupDecayedStateTable]:
        """Gets the most recent decayed state for a matchup (by team IDs) before a specific time."""
        t1, t2 = sorted([team1_id, team2_id])
        stmt = (
            select(TeamMatchupDecayedStateTable)
            .where(
                TeamMatchupDecayedStateTable.team1_id == t1,
                TeamMatchupDecayedStateTable.team2_id == t2,
            )
            .where(TeamMatchupDecayedStateTable.last_update_time < before_time)
            .order_by(desc(TeamMatchupDecayedStateTable.last_update_time))
            .limit(1)
        )
        res = await self._execute_and_handle_errors(
            stmt, f"fetching matchup decayed state for ids {t1} vs {t2} before {before_time}"
        )
        return res.scalars().first()

    async def get_player_hero_state_before(
        self, account_id: int, hero_id: int, before_time: datetime
    ) -> Optional[PlayerHeroDecayedStateTable]:
        """Gets the most recent decayed state for a player-hero combo before a specific time."""
        stmt = (
            select(PlayerHeroDecayedStateTable)
            .where(
                PlayerHeroDecayedStateTable.account_id == account_id,
                PlayerHeroDecayedStateTable.hero_id == hero_id,
            )
            .where(PlayerHeroDecayedStateTable.last_update_time < before_time)
            .order_by(desc(PlayerHeroDecayedStateTable.last_update_time))
            .limit(1)
        )
        res = await self._execute_and_handle_errors(
            stmt, f"fetching player-hero decayed state for acc={account_id} hero={hero_id} before {before_time}"
        )
        return res.scalars().first()

    async def get_hero_state_before(self, hero_id: int, before_time: datetime) -> Optional[HeroDecayedStateTable]:
        """Gets the most recent decayed state for a hero before a specific time."""
        stmt = (
            select(HeroDecayedStateTable)
            .where(HeroDecayedStateTable.hero_id == hero_id)
            .where(HeroDecayedStateTable.last_update_time < before_time)
            .order_by(desc(HeroDecayedStateTable.last_update_time))
            .limit(1)
        )
        res = await self._execute_and_handle_errors(
            stmt, f"fetching hero decayed state for hero={hero_id} before {before_time}"
        )
        return res.scalars().first()

    # --- PRIVATE UTILITY HELPERS ---

    async def _execute_and_handle_errors(self, stmt, operation_description: str):
        """Executes a SQLAlchemy statement with standardized error handling."""
        try:
            return await self.session.execute(stmt)
        except SQLAlchemyError as e:
            logger.error(f"DB error during '{operation_description}': {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during '{operation_description}': {e}", exc_info=True)
            raise

    async def _run_and_handle_errors(self, coro: Coroutine, operation_description: str):
        """Runs a coroutine with standardized error handling."""
        try:
            return await coro
        except SQLAlchemyError as e:
            logger.error(f"DB error during '{operation_description}': {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error during '{operation_description}': {e}", exc_info=True)
            raise
