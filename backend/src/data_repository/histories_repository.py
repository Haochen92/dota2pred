from typing import List, Optional
from .schemas.histories import PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import select, desc
from utils.set_logging import get_logger

logger = get_logger(__name__)


class HistoryRepository:
    def __init__(self, engine: AsyncEngine, default_history_limit: int = 20):
        self.engine = engine
        self.default_history_limit = default_history_limit

    # PLAYER HERO HISTORY
    async def get_player_hero_win_history(
        self,
        account_id: int,
        hero_id: int,
        before: Optional[int] = None, 
        after: Optional[int] = 0,
        limit: Optional[int] = None
    ) -> List[bool]:
        """
        Fetches win history, optionally filtering by time and limiting count.
        Results ordered by time DESC.
        """
        effective_limit = limit if limit is not None else self.default_history_limit

        if not account_id or not hero_id:
            logger.warning(...)
            return []

        logger.debug(f"Fetching DB history: acc={account_id}, hero={hero_id}, before={before}, after={after}, limit={effective_limit}")
        async with AsyncSession(self.engine) as session:
            try:
                stmt = (
                    select(PlayerHeroHistoryTable.win)
                    .where(PlayerHeroHistoryTable.account_id == account_id)
                    .where(PlayerHeroHistoryTable.hero_id == hero_id)
                )

                if after is not None:
                    stmt = stmt.where(PlayerHeroHistoryTable.match_start_time > after)
                if before is not None:
                    stmt = stmt.where(PlayerHeroHistoryTable.match_start_time < before)

                stmt = (
                    stmt.order_by(desc(PlayerHeroHistoryTable.match_start_time))
                    .limit(effective_limit) 
                )
                result = await session.execute(stmt)
                win_history = result.scalars().all()
                logger.debug(f"Found {len(win_history)} history entries...")
                return win_history
            except Exception as e:
                logger.error(f"DB error fetching player-hero history (...): {e}", exc_info=True)
                raise e


    async def add_player_hero_match_outcome(
        self,
        account_id: int,
        hero_id: int,
        match_id: int,
        win: bool,
        match_start_time: float
    ):
        """Persists a single player-hero match outcome."""
        logger.debug(f"Adding history to DB: ...")
        async with AsyncSession(self.engine) as session:
             try:
                 # Use the correct table model class name
                 stmt = insert(PlayerHeroHistoryTable).values(
                     account_id=account_id,
                     hero_id=hero_id,
                     match_id=match_id,
                     win=win,
                     match_start_time=match_start_time
                 ).on_conflict_do_nothing(index_elements=['match_id', 'hero_id', 'account_id'])

                 await session.execute(stmt)
                 await session.commit()
             except Exception as e:
                 await session.rollback()
                 logger.error(f"DB error adding player-hero history (...): {e}", exc_info=True)
                 raise
    
    # TEAM HISTORY
    async def get_team_history(
        self, 
        team_name: str,
        before: Optional[int] = None, 
        after: Optional[int] = 0,
        limit: Optional[int] = None
    ):
        effective_limit = limit if limit is not None else self.default_history_limit
        async with AsyncSession(self.engine) as session:
            stmt = select(TeamHistoryTable.win).where(
                TeamHistoryTable.team_name == team_name
            )
            
            if after is not None:
                stmt = stmt.where(TeamHistoryTable.match_start_time > after)
            if before is not None:
                stmt = stmt.where(TeamHistoryTable.match_start_time < before)

            stmt = (
                stmt.order_by(desc(TeamHistoryTable.match_start_time))
                .limit(effective_limit) 
            )
            result = await session.execute(stmt)
            team_history = result.scalars().all()
            logger.debug(f"Found {len(team_history)} history entries...")
            return team_history
        
    
    async def get_team_matchup_history(
        self, 
        team_one: str, 
        team_two: str,
        before: Optional[int] = None, 
        after: Optional[int] = 0,
        limit: Optional[int] = None
    ):
        async with AsyncSession(self.engine) as session:
            
            effective_limit = limit if limit is not None else self.default_history_limit
            
            stmt = select(TeamMatchupHistoryTable.win).where(
                TeamMatchupHistoryTable.team1_name == team_one,
                TeamMatchupHistoryTable.team2_name == team_two
            )
            
            if after is not None:
                stmt = stmt.where(TeamMatchupHistoryTable.match_start_time > after)
            if before is not None:
                stmt = stmt.where(TeamMatchupHistoryTable.match_start_time < before)

            stmt = (
                stmt.order_by(desc(TeamMatchupHistoryTable.match_start_time))
                .limit(effective_limit) # Use the calculated limit for this query
            )
            result = await session.execute(stmt)
            matchup_history = result.scalars().all()
            logger.debug(f"Found {len(matchup_history)} history entries...")
            return matchup_history
        
    async def add_team_match_outcome(
        self,
        team_name: str,
        match_id: int,
        win: bool,
        match_start_time: float
    ):
        async with AsyncSession(self.engine) as session:
             try:
                 stmt = insert(TeamHistoryTable).values(
                     team_name=team_name,
                     match_id=match_id,
                     win=win,
                     match_start_time=match_start_time
                 ).on_conflict_do_nothing(index_elements=['team_name', 'match_id'])

                 await session.execute(stmt)
                 await session.commit()
             except Exception as e:
                 await session.rollback()
                 logger.error(f"DB error adding team history (...): {e}", exc_info=True)
                 raise
        
        
        
    async def add_team_match_up_outcome(
        self,
        team_one: str,
        team_two: str,
        match_id: int,
        win: bool,
        match_start_time: float
    ):
        async with AsyncSession(self.engine) as session:
             try:
                 stmt = insert(TeamMatchupHistoryTable).values(
                     team1_name=team_one,
                     team2_name=team_two,
                     match_id=match_id,
                     win=win,
                     match_start_time=match_start_time
                 ).on_conflict_do_nothing(index_elements=['team1_name','team2_name' ,'match_id'])

                 await session.execute(stmt)
                 await session.commit()
             except Exception as e:
                 await session.rollback()
                 logger.error(f"DB error adding team matchup history (...): {e}", exc_info=True)
                 raise