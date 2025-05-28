from typing import Set, Dict, Any, Optional, List, Coroutine
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.utils.async_utils import run_updates_as_group, get_outcome_concurrently
from dota_oracle.data_transformation.live_match_parser import parse_live_league_games
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.data_repository.heroes_repository import HeroesRepository
from dota_oracle.data_repository.schemas import MatchTable
from dota_oracle.pydantic_models.live_league_games import LiveLeagueGame
from .redis_service import RedisService

# data extraction
from dota_oracle.data_extraction.fetch_live_leagues import fetch_live_league_games

logger = get_logger(__name__)

class NewMatchOrchestrator:
    def __init__(self, redis_service: RedisService, storage: MatchRepository, hero_repo: HeroesRepository ):
        self.redis = redis_service
        self.storage = storage
        self.hero_repo = hero_repo
        
        # Initialization Validation
        if not all([redis_service, storage, hero_repo]):
            raise ValueError("All dependencies must be provided")
        
    async def run_new_match_cycle(self) -> int:   
        
        curr_matches = await self._fetch_current_matches()
        if not curr_matches:
            logger.info("there are currently no live matches")
            return 0
        logger.info(f"found {len(curr_matches)} new matches...")
        
        new_matches = await self._filter_new_matches(curr_matches)
        
        transformed_new_matches = await self._transform_match_data(new_matches)
        
        task_dict: Dict[int, Coroutine[Any, Any, bool]] = {}
        
        for match_data in transformed_new_matches:
            match_id = match_data.match_id
            try:
                task_dict[match_id] = self._store_and_update_redis(match_data=match_data, match_id=match_id)
            except Exception as e:
                logger.error(f"Error encounted while adding match {match_id} to task group")
                continue
            
        outcomes: Dict[int, bool | Exception] = await get_outcome_concurrently(task_dict)
        
        success_count = sum(1 for outcome in outcomes.values() if outcome)
        failure_count = sum(1 for outcome in outcomes.values() if not outcome)
        
        logger.info(f"Successfully processed {success_count} new matches, with {failure_count} failures")
        return success_count
    
    async def _fetch_current_matches(self) -> List[LiveLeagueGame]:
        try:
            curr_games = await fetch_live_league_games()
            if not curr_games:
                return []
            return curr_games
        except Exception as e:
            logger.warning(f"Error fetching matches from API, {e}", exc_info=True)
            raise
        
        
    async def _transform_match_data(self, live_match_data: List[LiveLeagueGame]) -> List[MatchTable]:
        if not live_match_data:
            logger.warning(f"Empty live_match_data passed to data transformer")
            return []
        try:
            transformed_data = await parse_live_league_games(live_match_data, self.hero_repo)
            return transformed_data
        except Exception as e:
            logger.error(f"Unable to transform live_match_data, error: {e}", exc_info=True)
            raise
        
    async def _filter_new_matches(self, curr_matches: List[LiveLeagueGame]) -> List[LiveLeagueGame]:
        curr_match_ids = [match.match_id for match in curr_matches]
        new_match_set: Set[int] = await self.redis.update_live_match_set_and_get_new(curr_match_ids)
        if not new_match_set:
            logger.info("No new matches found")
            return []
        
        logger.info(f"Found {len(new_match_set)} new matches...")
        new_matches = [match for match in curr_matches if match.match_id in new_match_set]
        return new_matches
    
    async def _store_and_update_redis(self, match_data: MatchTable, match_id: int) -> bool:
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
        except Exception as e: # Catch any other exceptions
            logger.error(f"Unexpected error processing match {match_id}: {e}", exc_info=True)
            return False