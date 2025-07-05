from typing import List, Set
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.live_games.schema import LiveLeagueGame, OngoingLeagueGame
from dota_oracle_pipeline.data_extraction.fetch_live_leagues import fetch_live_league_games
from ..services.redis_service import RedisService
from dota_oracle_common.models.pipeline import NewMatchWorkItem
from pydantic import ValidationError

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
        ongoing_matches = await self._fetch_ongoing_matches()
        if not ongoing_matches:
            logger.info("No live matches found")
            return []

        logger.info(f"Found {len(ongoing_matches)} live matches")

        # Filter for new matches
        new_matches = await self._filter_new_matches(ongoing_matches)
        if not new_matches:
            logger.info("No new matches found")
            return []

        logger.info(f"Found {len(new_matches)} new matches")

        # Create work items
        work_items = [NewMatchWorkItem(live_match_data=match, match_id=match.match_id) for match in new_matches]

        return work_items

    async def _fetch_ongoing_matches(self) -> List[OngoingLeagueGame]:
        """Fetches current live league games from API & extract ongoing matches"""
        try:
            curr_games = await fetch_live_league_games()
            ongoing_games = await self._extract_ongoing_matches(curr_games)
            return ongoing_games
        except Exception as e:
            logger.warning(f"Error fetching matches from API: {e}", exc_info=True)
            raise

    async def _extract_ongoing_matches(self, all_curr_games: List[LiveLeagueGame]) -> List[OngoingLeagueGame]:
        ongoing_games_list: List[OngoingLeagueGame] = []
        for game in all_curr_games:
            try:
                ongoing_game = OngoingLeagueGame.model_validate(game.model_dump())
                ongoing_games_list.append(ongoing_game)
            except ValidationError:
                logger.info(f"match {game.match_id} is live but game has not started")
                continue
            except Exception:
                raise
        return ongoing_games_list

    async def _filter_new_matches(self, curr_matches: List[OngoingLeagueGame]) -> List[OngoingLeagueGame]:
        """Filters current matches to return only new ones."""
        curr_match_ids = [match.match_id for match in curr_matches]
        new_match_set: Set[int] = await self.redis.update_live_match_set_and_get_new(curr_match_ids)

        if not new_match_set:
            return []

        new_matches = [match for match in curr_matches if match.match_id in new_match_set]
        return new_matches
