from typing import List, Set
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.live_games.schema import LiveLeagueGame, OngoingLeagueGame
from dota_oracle_pipeline.data_extraction.api_clients.steam_api import SteamClient
from dota_oracle_pipeline.data_extraction.fetch_live_leagues import fetch_live_league_games
from ..redis_services.redis_service import RedisService
from pydantic import ValidationError

logger = get_logger(__name__)


class NewMatchDataProvider:
    """Data provider for new match processing pipeline."""

    def __init__(self, redis_service: RedisService, steam_client: SteamClient):
        self.redis = redis_service
        self.steam_client = steam_client

    async def get_new_ongoing_matches(self) -> List[OngoingLeagueGame]:
        """
        Fetches current live matches and filters for new, ongoing ones.

        Returns:
            List of OngoingLeagueGames
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

        return new_matches

    async def _fetch_ongoing_matches(self) -> List[OngoingLeagueGame]:
        """Fetches current live league games from API & extract ongoing matches"""
        try:
            curr_games: List[LiveLeagueGame] = await fetch_live_league_games(self.steam_client)
            ongoing_games = await self._extract_ongoing_matches(curr_games)
            return ongoing_games
        except Exception as e:
            logger.warning(f"Error fetching matches from API: {e}", exc_info=True)
            return []

    async def _extract_ongoing_matches(self, all_curr_games: List[LiveLeagueGame]) -> List[OngoingLeagueGame]:
        ongoing_games_list: List[OngoingLeagueGame] = []
        for game in all_curr_games:
            try:
                ongoing_game = OngoingLeagueGame.model_validate(game.model_dump())
                ongoing_games_list.append(ongoing_game)
            except ValidationError as e:
                logger.debug(
                    f"Skipping match {game.match_id}: draft not started or invalid (e.g. duplicate heroes). {e}"
                )
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
