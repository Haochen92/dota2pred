from typing import Set, Dict, Any, Optional, List, Coroutine
from utils.set_logging import get_logger
from utils.async_utils import run_updates_concurrently, run_updates_as_group
from data_repository.match_repository import MatchRepository
from .redis_service import RedisService

# data extraction
from data_extraction.fetch_live_leagues import fetch_live_league_games, LiveLeagueGame

logger = get_logger(__name__)

class NewMatchOrchestrator:
    def __init__(self, redis_service: RedisService, storage: MatchRepository):
        self.redis = redis_service
        self.storage = storage
        
    async def run_new_match_cycle(self) -> int:   
        
        curr_matches = await self._fetch_current_matches()
        if not curr_matches:
            return 0
        logger.info(f"found {len(curr_matches)} new matches...")
        
        new_match_set: Set[int] = await self.redis.update_live_match_set_and_get_new(curr_matches.keys())
        if not new_match_set:
            logger.info("No new matches found")
            return 0
        
        logger.info(f"Found {len(new_match_set)} new matches...")
        
        task_lists: List[Coroutine[Any, Any, None]] = []
        for match_id in new_match_set:
            try:
                match_data = curr_matches.get(match_id, {})
                if not match_data:
                    raise ValueError(f"{match_id} not found in current_matches")
                task_lists.append(self._store_and_update_redis(match_data, match_id))
            except Exception as e:
                logger.error(f"Error encounted while adding match {match_id} to task group")
                continue
            
        outcomes = await run_updates_concurrently(task_lists)
        
        success_count = 0
        failure_count = 0
        for outcome in outcomes:
            if outcome:
                success_count += 1
            else:
                failure_count += 1
        
        logger.info(f"Successfully processed {success_count} new matches, with {failure_count} failures")
        return success_count
    
    async def _store_and_update_redis(self, match_data: Dict[str, Any], match_id: int) -> bool:
        task_group = [
            self.storage.insert_match_details(match_data),
            self.redis.add_match_for_processing(match_id)
        ]
        try:
            await run_updates_as_group(task_group)
            return True
        except ExceptionGroup as eg:
            for i, exc in enumerate(eg.exceptions):
                logger.error(f"Exception {i+1}: {type(exc).__name__} - {exc}")
            return False 
    
    
    async def _fetch_current_matches(self) -> Optional[Dict[int, Dict[str, Any]]]:
        try:
            curr_games: List[LiveLeagueGame] = await fetch_live_league_games()
            curr_match_dict: Dict[int, Dict[str, Any]] = {item.match_id : item.model_dump() for item in curr_games}
            
            logger.info(f"Fetched {len(curr_match_dict)} live matches.")
            return curr_match_dict
        except Exception as e:
            logger.warning(f"Error fetching matches from API, {e}", exc_info=True)
            return {}