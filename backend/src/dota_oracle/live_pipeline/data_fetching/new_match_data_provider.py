from typing import List, Set
from dota_oracle.utils.set_logging import get_logger
from dota_oracle.models.live_games.schema import LiveLeagueGame
from dota_oracle.data_extraction.fetch_live_leagues import fetch_live_league_games
from ..redis_service import RedisService
from dota_oracle.models.pipeline import NewMatchWorkItem

logger = get_logger(__name__)

class NewMatchDataProvider:
    """Data provider for new match processing pipeline."""
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
    
    async def get_work_items(self) -> List[NewMatchWorkItem]:
        """
        Fetches current live matches and filters for new ones.
        
        Returns:
            List of NewMatchWorkItem for processing
        """
        # Fetch current live matches
        curr_matches = await self._fetch_current_matches()
        if not curr_matches:
            logger.info("No live matches found")
            return []
        
        logger.info(f"Found {len(curr_matches)} live matches")
        
        # Filter for new matches
        new_matches = await self._filter_new_matches(curr_matches)
        if not new_matches:
            logger.info("No new matches found")
            return []
        
        logger.info(f"Found {len(new_matches)} new matches")
        
        # Create work items
        work_items = [
            NewMatchWorkItem(
                live_match_data=match,
                match_id=match.match_id
            )
            for match in new_matches
        ]
        
        return work_items
    
    async def _fetch_current_matches(self) -> List[LiveLeagueGame]:
        """Fetches current live league games from API."""
        try:
            curr_games = await fetch_live_league_games()
            return curr_games or []
        except Exception as e:
            logger.warning(f"Error fetching matches from API: {e}", exc_info=True)
            raise
    
    async def _filter_new_matches(self, curr_matches: List[LiveLeagueGame]) -> List[LiveLeagueGame]:
        """Filters current matches to return only new ones."""
        curr_match_ids = [match.match_id for match in curr_matches]
        new_match_set: Set[int] = await self.redis.update_live_match_set_and_get_new(curr_match_ids)
        
        if not new_match_set:
            return []
        
        new_matches = [match for match in curr_matches if match.match_id in new_match_set]
        return new_matches