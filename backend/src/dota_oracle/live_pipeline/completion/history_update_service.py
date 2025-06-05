from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.utils import get_logger, run_updates_as_group
from dota_oracle.utils.time_utils import to_utc_datetime_object
from typing import List, Coroutine, Any
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from dota_oracle.models.match import MatchTable, MatchOutcomeTable

logger = get_logger(__name__)

class HistoryUpdateService:
    def __init__(self, db_engine: AsyncEngine):
        self.engine = db_engine            
          
    async def update_histories(self, match_id: int) -> None:
        
        try:
            async with AsyncSession(self.engine) as session:
                async with session.begin():
                    history_repository = HistoryRepository(session=session)
                    
                    # Get completed matches from db
                    match_details = await self._get_completed_match_details(match_id, session)
                    match_outcome = match_details.outcome
                    if not match_outcome:
                        raise ValueError(f"Match outcome for {match_id} not in database, unable to proceed")
                    
                    # update team histories
                    await self._update_team_histories(history_repository, match_details, match_outcome)
                    
                    # update player_hero_histories
                    await self._update_player_hero_histories(history_repository, match_details, match_outcome)
        except Exception as e:
            raise e
        
    async def _update_team_histories(
        self,
        history_repository: HistoryRepository, 
        match_details:MatchTable, 
        match_outcome: MatchOutcomeTable
    ) -> None: 
        team_task_group: List[Coroutine[Any, Any, None]] = []
        try:
            team_task_group.append(history_repository.add_team_match_outcome(
                team_name=match_details.radiant_name,
                match_id=match_details.match_id,
                win=match_outcome.radiant_win,
                match_start_time=to_utc_datetime_object(match_details.start_time)
            ))
                        
            team_task_group.append(history_repository.add_team_match_outcome(
                team_name=match_details.dire_name,
                match_id=match_details.match_id,
                win= not match_outcome.radiant_win,
                match_start_time=to_utc_datetime_object(match_details.start_time)
            ))
                        
            # team match_up histories
            team_task_group.append(history_repository.add_team_matchup_outcome(
                team_one=match_details.radiant_name,
                team_two=match_details.dire_name,
                match_id=match_details.match_id,
                win=match_outcome.radiant_win,
                match_start_time=to_utc_datetime_object(match_details.start_time)
            ))
            
            await run_updates_as_group(team_task_group)
        except Exception as e:
            logger.error(f"Error updating team_history for match {match_details.match_id} {e}", exc_info=True)
            raise e
        
    async def _update_player_hero_histories(
        self,
        history_repository: HistoryRepository,
        match_details:MatchTable, 
        match_outcome: MatchOutcomeTable
    ):
        player_hero_task_group: List[Coroutine[Any, Any, None]] = []
        
        try:
            for i in list(range(0,5)) + list(range(128, 133)):
                account_id_str = f"slot_{i}_account_id"
                hero_id_str = f"slot_{i}_hero_id"
                account_id = getattr(match_details, account_id_str)
                hero_id = getattr(match_details, hero_id_str)
                
                if i < 5:
                    win = match_outcome.radiant_win
                else:
                    win = not match_outcome.radiant_win
                    
                player_hero_task_group.append(history_repository.add_player_hero_match_outcome(
                    account_id=account_id,
                    hero_id=hero_id,
                    match_id=match_details.match_id,
                    win=win,
                    match_start_time=to_utc_datetime_object(match_details.start_time)
                ))
            await run_updates_as_group(player_hero_task_group)
        except Exception as e:
            logger.error(f"Error updating player histories for match {match_details.match_id}: {e}", exc_info=True)
            raise e
        
    async def _get_completed_match_details(self, match_id: int, session: AsyncSession) -> MatchTable:
        match_repository = MatchRepository(session=session)
        
        res = await match_repository.get_match_details(
            input_id_list=[match_id],
            relationship_fields=['outcome']
        )
        
        if not res:
            raise ValueError(f"Match {match_id} cannot be found in database, exiting function")
        
        completed_match_details = res[0]
        
        return completed_match_details  