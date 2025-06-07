from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.utils import get_logger, TaskRunner
from dota_oracle.utils.time_utils import to_utc_datetime_object
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from dota_oracle.models.match import MatchTable, MatchOutcomeTable
from dota_oracle.models.utils import AsyncTask

logger = get_logger(__name__)

class HistoryUpdateService: 
         
    async def update_histories(self, db_session: AsyncSession, match_id: int) -> None:
        try:
            history_repository = HistoryRepository(session=db_session)
                    
            # Get completed matches from db
            match_details = await self._get_completed_match_details(match_id, db_session)
            match_outcome = match_details.outcome
            if not match_outcome:
                raise ValueError(f"Match outcome for {match_id} not in database, unable to proceed")
            
            update_history_task: List[AsyncTask] = [
                AsyncTask(key='update_team_histories', coro=self._update_team_histories(history_repository, match_details, match_outcome)),
                AsyncTask(key='update_player_hero_histories', coro=self._update_player_hero_histories(history_repository, match_details, match_outcome))
            ]
            
            await TaskRunner.run_as_group(update_history_task)
        except Exception as e:
            logger.error("History update failed")
            raise e
        
    async def _update_team_histories(
        self,
        history_repository: HistoryRepository, 
        match_details: MatchTable, 
        match_outcome: MatchOutcomeTable
    ) -> None: 
        team_tasks = [
            AsyncTask(
                key='radiant_team_outcome',
                coro=history_repository.add_team_match_outcome(
                    team_name=match_details.radiant_name,
                    match_id=match_details.match_id,
                    win=match_outcome.radiant_win,
                    match_start_time=to_utc_datetime_object(match_details.start_time)
                )
            ),
            AsyncTask(
                key='dire_team_outcome',
                coro=history_repository.add_team_match_outcome(
                    team_name=match_details.dire_name,
                    match_id=match_details.match_id,
                    win=not match_outcome.radiant_win,
                    match_start_time=to_utc_datetime_object(match_details.start_time)
                )
            ),
            AsyncTask(
                key='team_matchup_outcome',
                coro=history_repository.add_team_matchup_outcome(
                    team_one=match_details.radiant_name,
                    team_two=match_details.dire_name,
                    match_id=match_details.match_id,
                    win=match_outcome.radiant_win,
                    match_start_time=to_utc_datetime_object(match_details.start_time)
                )
            )
        ]
        
        try:
            await TaskRunner.run_as_group(team_tasks)
        except Exception as e:
            logger.error(f"Error updating team_history for match {match_details.match_id}: {e}", exc_info=True)
            raise

    async def _update_player_hero_histories(
        self,
        history_repository: HistoryRepository,
        match_details: MatchTable, 
        match_outcome: MatchOutcomeTable
    ) -> None:
        player_hero_tasks = []
        
        try:
            # Process radiant players (slots 0-4) and dire players (slots 128-132)
            for i in list(range(0, 5)) + list(range(128, 133)):
                account_id = getattr(match_details, f"slot_{i}_account_id")
                hero_id = getattr(match_details, f"slot_{i}_hero_id")
                
                # Radiant players win if radiant_win is True, dire players win if radiant_win is False
                win = match_outcome.radiant_win if i < 5 else not match_outcome.radiant_win
                
                player_hero_tasks.append(
                    AsyncTask(
                        key=f'player_hero_outcome_slot_{i}',
                        coro=history_repository.add_player_hero_match_outcome(
                            account_id=account_id,
                            hero_id=hero_id,
                            match_id=match_details.match_id,
                            win=win,
                            match_start_time=to_utc_datetime_object(match_details.start_time)
                        )
                    )
                )
                
            await TaskRunner.run_as_group(player_hero_tasks)
        except Exception as e:
            logger.error(f"Error updating player histories for match {match_details.match_id}: {e}", exc_info=True)
            raise
        
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