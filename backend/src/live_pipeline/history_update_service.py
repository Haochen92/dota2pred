from data_repository.histories_repository import HistoryRepository
from pydantic_models.match import MatchesAPIResponse
from utils.set_logging import get_logger

logger = get_logger(__name__)

class HistoryUpdateService:
    def __init__(self, history_repository: HistoryRepository):
        self.storage = history_repository
    
    async def update_histories(self, match_details: MatchesAPIResponse) -> None:
        try:
            # team histories
            await self.storage.add_team_match_outcome(
                team_name=match_details.radiant_name,
                match_id=match_details.match_id,
                win=match_details.radiant_win,
                match_start_time=match_details.start_time
            )
            await self.storage.add_team_match_outcome(
                team_name=match_details.dire_name,
                match_id=match_details.match_id,
                win= not match_details.radiant_win,
                match_start_time=match_details.start_time
            )
            
            # team match_up histories
            await self.storage.add_team_match_up_outcome(
                team_one=match_details.radiant_name,
                team_two=match_details.dire_name,
                match_id=match_details.match_id,
                win=match_details.radiant_win,
                match_start_time=match_details.start_time
            )
            
        except Exception as e:
            logger.error(f"Error updating team_history for {match_details.match_id}: {e}", exc_info=True)
            raise e
        
        try:
            for player_data in match_details.players:
                player_slot:int = player_data.player_slot
                account_id = player_data.account_id
                hero_id=player_data.hero_id
                
                if player_slot in range(0, 5):
                    win = match_details.radiant_win
                else:
                    win = not match_details.radiant_win
                    
                await self.storage.add_player_hero_match_outcome(
                    account_id=account_id,
                    hero_id=hero_id,
                    match_id=match_details.match_id,
                    win=win,
                    match_start_time=match_details.start_time
                )
        except Exception as e:
            logger.error(f"Error updating player histories for match {match_details.match_id}: {e}", exc_info=True)
            raise e