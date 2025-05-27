from typing import List, Optional
from .schemas.histories import PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select, desc
from dota_oracle.utils.set_logging import get_logger
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

logger = get_logger(__name__)

class HistoryRepository:
    """
    Repository for accessing and storing historical match outcome data
    for players, heroes, teams, and matchups.
    """
    def __init__(self, engine: AsyncEngine, default_history_limit: int = 20):
        self.engine = engine
        self.default_history_limit = default_history_limit

    # --- PLAYER HERO HISTORY ---
    async def get_player_hero_win_history(
        self,
        account_id: int,
        hero_id: int,
        before: Optional[datetime] = None, 
        after: Optional[datetime] = None, 
        limit: Optional[int] = None
    ) -> List[bool]:
        """
        Fetches win history (list of booleans) for a specific player/hero combination.
        Optionally filters by time (Unix timestamp) and limits count.
        Results ordered by time DESC (most recent first).

        Args:
            account_id: The player's account ID.
            hero_id: The hero's ID.
            before: Optional Unix timestamp to get history before this time.
            after: Optional Unix timestamp to get history after this time (defaults to 0).
            limit: Optional maximum number of history entries to return.

        Returns:
            A list of boolean win statuses, ordered most recent first. Empty list on error or no data.
        """
        effective_limit = limit if limit is not None else self.default_history_limit

        if not account_id or not hero_id:
            logger.warning("get_player_hero_win_history called with invalid account_id or hero_id.")
            return []

        logger.debug(f"Fetching player-hero history: acc={account_id}, hero={hero_id}, before={before}, after={after}, limit={effective_limit}")
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            try:
                stmt = (
                    select(PlayerHeroHistoryTable.win)
                    .where(PlayerHeroHistoryTable.account_id == account_id)
                    .where(PlayerHeroHistoryTable.hero_id == hero_id)
                )

                if after: 
                    stmt = stmt.where(PlayerHeroHistoryTable.start_time > after)
                if before:
                    stmt = stmt.where(PlayerHeroHistoryTable.start_time < before)

                stmt = (
                    stmt.order_by(desc(PlayerHeroHistoryTable.start_time))
                    .limit(effective_limit)
                )
                result = await session.execute(stmt)
                win_history: List[bool] = list(result.scalars().all())
                logger.debug(f"Found {len(win_history)} player-hero history entries for acc={account_id}, hero={hero_id}.")
                return win_history
            except SQLAlchemyError as e: 
                logger.error(f"DB error fetching player-hero history for acc={account_id}, hero={hero_id}: {e}", exc_info=True)
                raise e
            except Exception as e: 
                logger.error(f"Unexpected error fetching player-hero history for acc={account_id}, hero={hero_id}: {e}", exc_info=True)
                raise e 


    async def add_player_hero_match_outcome(
        self,
        account_id: int,
        hero_id: int,
        match_id: int,
        win: bool,
        match_start_time: datetime 
    ) -> None:
        """
        Persists a single player-hero match outcome using INSERT ... ON CONFLICT DO NOTHING.
        """
        logger.debug(f"Adding player-hero history: acc={account_id}, hero={hero_id}, match={match_id}")
        async with AsyncSession(self.engine) as session:
             async with session.begin(): 
                try:
                    stmt = insert(PlayerHeroHistoryTable).values(
                        account_id=account_id,
                        hero_id=hero_id,
                        match_id=match_id,
                        win=win,
                        start_time=match_start_time
                    ).on_conflict_do_nothing(
                        index_elements=['match_id', 'hero_id', 'account_id'] # Ensure this matches your unique constraint
                    )
                    await session.execute(stmt)
                except SQLAlchemyError as e: 
                    logger.error(f"DB error adding player-hero history for match={match_id}, acc={account_id}: {e}", exc_info=True)
                    raise 
                except Exception as e: 
                    logger.error(f"Unexpected error adding player-hero history for match={match_id}, acc={account_id}: {e}", exc_info=True)
                    raise

    # --- TEAM HISTORY ---
    async def get_team_history(
        self,
        team_name: str,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[bool]:
        """
        Fetches win history (list of booleans) for a specific team.
        Args are similar to get_player_hero_win_history.
        """
        effective_limit = limit if limit is not None else self.default_history_limit

        if not team_name:
            logger.warning("get_team_history called with empty team_name.")
            return []

        logger.debug(f"Fetching team history: team='{team_name}', before={before}, after={after}, limit={effective_limit}")
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            try:
                stmt = select(TeamHistoryTable.win).where(
                    TeamHistoryTable.team_name == team_name
                )

                if after:
                    stmt = stmt.where(TeamHistoryTable.start_time > after)
                if before:
                    stmt = stmt.where(TeamHistoryTable.start_time < before)

                stmt = (
                    stmt.order_by(desc(TeamHistoryTable.start_time))
                    .limit(effective_limit)
                )
                result = await session.execute(stmt)
                team_history: List[bool] = list(result.scalars().all())
                logger.debug(f"Found {len(team_history)} history entries for team='{team_name}'.")
                return team_history
            except SQLAlchemyError as e:
                logger.error(f"DB error fetching team history for team='{team_name}': {e}", exc_info=True)
                raise e
            except Exception as e:
                logger.error(f"Unexpected error fetching team history for team='{team_name}': {e}", exc_info=True)
                raise e


    async def get_team_matchup_history(
        self,
        team_one: str,
        team_two: str,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[bool]:
        """
        Fetches win history (list of booleans) for a specific team vs team matchup (team_one's perspective).
        """
        effective_limit = limit if limit is not None else self.default_history_limit

        if not team_one or not team_two:
             logger.warning("get_team_matchup_history called with empty team names.")
             return []

        logger.debug(f"Fetching matchup history: {team_one} vs {team_two}, before={before}, after={after}, limit={effective_limit}")
        async with AsyncSession(self.engine, expire_on_commit=False) as session:
            try:
                sorted_teams = sorted([team_one, team_two])

                stmt = select(TeamMatchupHistoryTable.win).where(
                   TeamMatchupHistoryTable.team1_name == sorted_teams[0],
                   TeamMatchupHistoryTable.team2_name == sorted_teams[1]
                )

                if after:
                    stmt = stmt.where(TeamMatchupHistoryTable.start_time > after)
                if before:
                    stmt = stmt.where(TeamMatchupHistoryTable.start_time < before)

                stmt = (
                    stmt.order_by(desc(TeamMatchupHistoryTable.start_time))
                    .limit(effective_limit)
                )
                result = await session.execute(stmt)
                matchup_history: List[bool] = list(result.scalars().all())
                logger.debug(f"Found {len(matchup_history)} matchup history entries for {team_one} vs {team_two}.")
                return matchup_history
            except SQLAlchemyError as e:
                logger.error(f"DB error fetching matchup history for {team_one} vs {team_two}: {e}", exc_info=True)
                raise e
            except Exception as e:
                logger.error(f"Unexpected error fetching matchup history for {team_one} vs {team_two}: {e}", exc_info=True)
                raise e

    async def add_team_match_outcome(
        self,
        team_name: Optional[str],
        match_id: int,
        win: bool,
        match_start_time: datetime
    ) -> None:
        """
        Persists a single team match outcome.
        """
        logger.debug(f"Adding team history: team='{team_name}', match={match_id}")
        if not team_name:
            logger.warning(f"Missing team name")
            return None
        async with AsyncSession(self.engine) as session:
             async with session.begin():
                try:
                    stmt = insert(TeamHistoryTable).values(
                        team_name=team_name,
                        match_id=match_id,
                        win=win,
                        start_time=match_start_time
                    ).on_conflict_do_nothing(
                        index_elements=['team_name', 'match_id'] 
                    )
                    await session.execute(stmt)
                except SQLAlchemyError as e:
                    logger.error(f"DB error adding team history for match={match_id}, team='{team_name}': {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error adding team history for match={match_id}, team='{team_name}': {e}", exc_info=True)
                    raise


    async def add_team_match_up_outcome(
        self,
        team_one: Optional[str],
        team_two: Optional[str],
        match_id: int,
        win: bool, # Assumes win is from team_one's perspective
        match_start_time: datetime
    ) -> None:
        """
        Persists a single team matchup outcome.
        Consider canonical ordering if A vs B and B vs A should be the same entry.
        """
        # Defensive canonical sorting even if calling function has sorted beforehand:
        if not team_one or not team_two:
            logger.warning(f"Missing team names for either of the teams")
            return
        sorted_teams = sorted([team_one, team_two])
        team1_name = sorted_teams[0]
        team2_name = sorted_teams[1]


        logger.debug(f"Adding matchup history: {team1_name} vs {team2_name}, match={match_id}")
        async with AsyncSession(self.engine) as session:
            async with session.begin():
                try:
                    stmt = insert(TeamMatchupHistoryTable).values(
                        team1_name=team1_name,
                        team2_name=team2_name,
                        match_id=match_id,
                        win=win, 
                        start_time=match_start_time
                    ).on_conflict_do_nothing(
                        index_elements=['team1_name','team2_name' ,'match_id']
                    )
                    await session.execute(stmt)
                except SQLAlchemyError as e:
                    logger.error(f"DB error adding team matchup history for match={match_id}, teams=({team1_name}, {team2_name}): {e}", exc_info=True)
                    raise
                except Exception as e:
                    logger.error(f"Unexpected error adding team matchup history for match={match_id}, teams=({team1_name}, {team2_name}): {e}", exc_info=True)
                    raise