from typing import List, Optional
from dota_oracle.models.histories import PlayerHeroHistoryTable, TeamHistoryTable, TeamMatchupHistoryTable
from sqlalchemy.ext.asyncio import AsyncSession
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
    
    Follows the Unit of Work pattern - accepts a session that manages transactions.
    """
    def __init__(self, session: AsyncSession, default_history_limit: int = 20):
        self.session = session
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
        """
        effective_limit = limit if limit is not None else self.default_history_limit

        if not account_id or not hero_id:
            logger.warning("get_player_hero_win_history called with invalid account_id or hero_id.")
            return []

        logger.debug(f"Fetching player-hero history: acc={account_id}, hero={hero_id}, before={before}, after={after}, limit={effective_limit}")
        
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
            
            result = await self.session.execute(stmt)
            win_history: List[bool] = list(result.scalars().all())
            
            logger.debug(f"Found {len(win_history)} player-hero history entries for acc={account_id}, hero={hero_id}.")
            return win_history
            
        except SQLAlchemyError as e: 
            logger.error(f"DB error fetching player-hero history for acc={account_id}, hero={hero_id}: {e}", exc_info=True)
            raise
        except Exception as e: 
            logger.error(f"Unexpected error fetching player-hero history for acc={account_id}, hero={hero_id}: {e}", exc_info=True)
            raise

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
        
        try:
            stmt = insert(PlayerHeroHistoryTable).values(
                account_id=account_id,
                hero_id=hero_id,
                match_id=match_id,
                win=win,
                start_time=match_start_time
            ).on_conflict_do_nothing(
                index_elements=['match_id', 'hero_id', 'account_id']
            )
            
            await self.session.execute(stmt)
            
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
        """
        effective_limit = limit if limit is not None else self.default_history_limit

        if not team_name:
            logger.warning("get_team_history called with empty team_name.")
            return []

        logger.debug(f"Fetching team history: team='{team_name}', before={before}, after={after}, limit={effective_limit}")
        
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
            
            result = await self.session.execute(stmt)
            team_history: List[bool] = list(result.scalars().all())
            
            logger.debug(f"Found {len(team_history)} history entries for team='{team_name}'.")
            return team_history
            
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching team history for team='{team_name}': {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching team history for team='{team_name}': {e}", exc_info=True)
            raise

    async def get_team_matchup_history(
        self,
        team_one: str,
        team_two: str,
        before: Optional[datetime] = None,
        after: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[bool]:
        """
        Fetches win history (list of booleans) for a specific team vs team matchup.
        Returns results from team_one's perspective.
        """
        effective_limit = limit if limit is not None else self.default_history_limit

        if not team_one or not team_two:
            logger.warning("get_team_matchup_history called with empty team names.")
            return []

        logger.debug(f"Fetching matchup history: {team_one} vs {team_two}, before={before}, after={after}, limit={effective_limit}")
        
        try:
            # Canonical ordering for consistent lookups
            sorted_teams = sorted([team_one, team_two])
            
            # If team_one is not the first in sorted order, we need to invert wins
            invert_wins = team_one != sorted_teams[0]

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
            
            result = await self.session.execute(stmt)
            matchup_history: List[bool] = list(result.scalars().all())
            
            # Invert wins if necessary to return from team_one's perspective
            if invert_wins:
                matchup_history = [not win for win in matchup_history]
            
            logger.debug(f"Found {len(matchup_history)} matchup history entries for {team_one} vs {team_two}.")
            return matchup_history
            
        except SQLAlchemyError as e:
            logger.error(f"DB error fetching matchup history for {team_one} vs {team_two}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching matchup history for {team_one} vs {team_two}: {e}", exc_info=True)
            raise

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
        if not team_name:
            logger.warning(f"Missing team name for match {match_id}")
            return
            
        logger.debug(f"Adding team history: team='{team_name}', match={match_id}")
        
        try:
            stmt = insert(TeamHistoryTable).values(
                team_name=team_name,
                match_id=match_id,
                win=win,
                start_time=match_start_time
            ).on_conflict_do_nothing(
                index_elements=['team_name', 'match_id'] 
            )
            
            await self.session.execute(stmt)
            
        except SQLAlchemyError as e:
            logger.error(f"DB error adding team history for match={match_id}, team='{team_name}': {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding team history for match={match_id}, team='{team_name}': {e}", exc_info=True)
            raise

    async def add_team_matchup_outcome(
        self,
        team_one: Optional[str],
        team_two: Optional[str],
        match_id: int,
        win: bool,  # From team_one's perspective
        match_start_time: datetime
    ) -> None:
        """
        Persists a single team matchup outcome.
        Win parameter is from team_one's perspective.
        """
        if not team_one or not team_two:
            logger.warning(f"Missing team names for match {match_id}")
            return
            
        # Canonical ordering for consistent storage
        sorted_teams = sorted([team_one, team_two])
        team1_name = sorted_teams[0]
        team2_name = sorted_teams[1]
        
        # If team_one is not first in sorted order, invert the win
        actual_win = win if team_one == team1_name else not win

        logger.debug(f"Adding matchup history: {team1_name} vs {team2_name}, match={match_id}")
        
        try:
            stmt = insert(TeamMatchupHistoryTable).values(
                team1_name=team1_name,
                team2_name=team2_name,
                match_id=match_id,
                win=actual_win,  # Store from team1's perspective
                start_time=match_start_time
            ).on_conflict_do_nothing(
                index_elements=['team1_name', 'team2_name', 'match_id']
            )
            
            await self.session.execute(stmt)
            
        except SQLAlchemyError as e:
            logger.error(f"DB error adding team matchup history for match={match_id}, teams=({team1_name}, {team2_name}): {e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Unexpected error adding team matchup history for match={match_id}, teams=({team1_name}, {team2_name}): {e}", exc_info=True)
            raise