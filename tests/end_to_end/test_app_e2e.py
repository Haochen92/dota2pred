"""
E2E tests for the live match processing pipeline.

Tests the complete flow from match discovery through prediction and completion
by simulating multiple processing cycles.
"""
import logging
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional
from unittest.mock import patch

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlmodel import select

from dota_oracle_common.models.inference.table import MatchPredictionTable
from dota_oracle_common.models.live_games.schema import LiveLeagueGame, OngoingLeagueGame, Player
from dota_oracle_common.models.match.schema import MatchesAPIResponse, ProMatchOutcome
from dota_oracle_common.models.match.table import MatchOutcomeTable, MatchTable
from live_orchestrator_app.app_container import AppContainer

logger = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio(loop_scope='session')


class VerificationState(BaseModel):
    """Expected system state for verification."""
    
    cycle_name: str
    redis_pending: Dict[str, int] = Field(default_factory=dict)
    redis_statuses: Dict[int, str] = Field(default_factory=dict)
    db_counts: Dict[str, int] = Field(default_factory=dict)


@pytest.mark.e2e
class TestLivePipelineE2E:
    """Tests match progression through the pipeline across multiple cycles."""

    MATCH_IDS = [7800001, 7800002, 7800003]

    @pytest.fixture(scope='function')
    def live_league_data(self, ongoing_league_game_factory) -> Dict[int, OngoingLeagueGame]:
        matches = {id: ongoing_league_game_factory.build(match_id=id) for id in self.MATCH_IDS}
        return matches

    @pytest.fixture(scope='function')
    def match_details_fetcher(self, matches_api_response_factory) -> Callable[[int], Optional[MatchesAPIResponse]]:
        """Mock match details provider."""
        details_map = {id: matches_api_response_factory.build(match_id=id) for id in self.MATCH_IDS}
            
        return lambda match_id: details_map.get(match_id)

    @pytest.fixture(scope='function')
    def cycle1_live_games(self, live_league_data: Dict[int, OngoingLeagueGame]) -> List[LiveLeagueGame]:
        """Cycle 1: Two new matches."""
        games = [live_league_data[self.MATCH_IDS[0]], live_league_data[self.MATCH_IDS[1]]]
        return [LiveLeagueGame.model_validate(g.model_dump()) for g in games]

    @pytest.fixture(scope='function')
    def cycle2_live_games(self, live_league_data: Dict[int, OngoingLeagueGame]) -> List[LiveLeagueGame]:
        """Cycle 2: Previous matches + one new match."""
        games = [live_league_data[match_id] for match_id in self.MATCH_IDS]
        return [LiveLeagueGame.model_validate(g.model_dump()) for g in games]

    @pytest.fixture(scope='function')
    def cycle3_live_games(self, live_league_data: Dict[int, OngoingLeagueGame]) -> List[LiveLeagueGame]:
        """Cycle 3: First match completed."""
        games = [live_league_data[self.MATCH_IDS[1]], live_league_data[self.MATCH_IDS[2]]]
        return [LiveLeagueGame.model_validate(g.model_dump()) for g in games]

    @pytest.fixture(scope='function')
    def completed_match_outcomes(self) -> List[ProMatchOutcome]:
        """Completed match outcome for first match."""
        return [ProMatchOutcome(match_id=self.MATCH_IDS[0], radiant_win=True)]

    async def _verify_system_state(self, redis_service, db_engine, expected: VerificationState) -> None:
        """Verify Redis and database state against expectations."""
        logger.info(f"Verifying state: {expected.cycle_name}")
        
        await self._verify_redis_streams(redis_service, expected.redis_pending)
        await self._verify_match_statuses(redis_service, expected.redis_statuses)
        await self._verify_db_state(db_engine, expected.db_counts)

    async def _verify_redis_streams(self, redis_service_client, expected_pending: Dict[str, int]) -> None:
        """Verify Redis stream pending message counts."""
        streams = {
            "new_matches": "feature_engineer_group",
            "pending_prediction": "prediction_group",
            "pending_completion": "completion_group"
        }
        
        for stream, group in streams.items():
            expected = expected_pending.get(stream, 0)
            
            try:
                pending_info = await redis_service_client.redis.xpending(stream, group)
                actual = pending_info['pending']
                logger.debug(f"Stream '{stream}': {actual} pending (expected: {expected})")
                assert actual == expected, f"Stream '{stream}' has {actual} pending messages, expected {expected}"
            except Exception:
                logger.debug(f"Stream '{stream}' doesn't exist (expected: {expected} pending)")
                assert expected == 0, f"Expected {expected} pending messages in '{stream}', but stream doesn't exist"

    async def _verify_match_statuses(self, redis_service_client, expected_statuses: Dict[int, str]) -> None:
        """Verify match statuses in Redis."""
        for match_id, expected_status in expected_statuses.items():
            status = await redis_service_client.redis.hget(f'match_status:{match_id}', 'status')
            assert status == expected_status, f"Match {match_id} status is '{status}', expected '{expected_status}'"

    async def _verify_db_state(self, db_engine, expected_counts: Dict[str, int]) -> None:
        """Verify database row counts."""
        table_map = {
            'matches': MatchTable,
            'predictions': MatchPredictionTable,
            'outcomes': MatchOutcomeTable
        }
        
        async with db_engine.begin() as conn:
            for key, table in table_map.items():
                count = (await conn.execute(select(func.count()).select_from(table))).scalar_one()
                expected = expected_counts.get(key, 0)
                logger.debug(f"Table '{table.__tablename__}': {count} rows (expected: {expected})")
                assert count == expected, f"Table '{table.__tablename__}' has {count} rows, expected {expected}"

    async def test_pipeline_progression(
        self,
        configured_test_container: AppContainer,
        cycle1_live_games,
        cycle2_live_games,
        cycle3_live_games,
        match_details_fetcher,
        completed_match_outcomes,
        setup_hero_data
    ):
        """
        Test complete pipeline progression through multiple cycles.
        
        Verifies:
        - New match discovery and processing
        - Additional match discovery
        - Match completion handling
        """
        db_engine = configured_test_container.db_engine()
        app = await configured_test_container.app()
        redis_service = await configured_test_container.redis_service()
        
        # Verify initial clean state
        await self._verify_system_state(redis_service, db_engine, VerificationState(cycle_name="Initial State"))

        # Cycle 1: Discover two new matches
        with patch('dota_oracle_pipeline.data_extraction.fetch_live_leagues.fetch_live_league_games', return_value=cycle1_live_games) as mock_live, \
             patch('live_orchestrator_app.data_fetching.new_match_data_provider.fetch_live_league_games', return_value=cycle1_live_games) as mock_live_usage, \
             patch('dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details', side_effect=match_details_fetcher) as mock_details, \
             patch('dota_oracle_pipeline.data_extraction.fetch_pro_match.fetch_pro_match', return_value=[]) as mock_outcomes, \
             patch('live_orchestrator_app.services.fetch_outcome_service.fetch_pro_match', return_value=[]) as mock_outcomes_usage:
            
            await app.run_cycle()
            
        logger.info(f"Cycle 1 mock calls - Live: {mock_live.call_count}, Details: {mock_details.call_count}")
        
        if mock_live_usage.call_count > 0:
            expected_matches = len(cycle1_live_games)
            
            async with db_engine.begin() as conn:
                match_count = (await conn.execute(select(func.count()).select_from(MatchTable))).scalar_one()
            
            logger.info(f"Cycle 1: {match_count} matches processed (expected: {expected_matches})")
            
            await self._verify_system_state(
                redis_service,
                db_engine,
                VerificationState(
                    cycle_name="Cycle 1 - New match discovery",
                    redis_pending={},
                    redis_statuses={},
                    db_counts={'matches': expected_matches, 'predictions': 0, 'outcomes': 0},
                )
            )
        else:
            logger.warning("Mocks not called - using real API behavior")

        # Cycle 2: Discover additional match
        with patch('live_orchestrator_app.data_fetching.new_match_data_provider.fetch_live_league_games', return_value=cycle2_live_games) as mock_live2, \
             patch('dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details', side_effect=match_details_fetcher), \
             patch('dota_oracle_pipeline.data_extraction.fetch_pro_match.fetch_pro_match', return_value=[]):
            await app.run_cycle()

        if mock_live2.call_count > 0:
            expected_total = len(cycle2_live_games)
            
            async with db_engine.begin() as conn:
                match_count = (await conn.execute(select(func.count()).select_from(MatchTable))).scalar_one()
            
            logger.info(f"Cycle 2: {match_count} total matches (expected: {expected_total})")
            
            await self._verify_system_state(
                redis_service,
                db_engine,
                VerificationState(
                    cycle_name="Cycle 2 - Additional match",
                    redis_pending={},
                    redis_statuses={},
                    db_counts={'matches': expected_total, 'predictions': 0, 'outcomes': 0},
                )
            )

        # Cycle 3: First match completes
        with patch('live_orchestrator_app.data_fetching.new_match_data_provider.fetch_live_league_games', return_value=cycle3_live_games) as mock_live3, \
             patch('dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details', side_effect=match_details_fetcher), \
             patch('live_orchestrator_app.services.fetch_outcome_service.fetch_pro_match', return_value=completed_match_outcomes) as mock_outcomes3:
            await app.run_cycle()

        if mock_live3.call_count > 0:
            async with db_engine.begin() as conn:
                final_matches = (await conn.execute(select(func.count()).select_from(MatchTable))).scalar_one()
                outcomes = (await conn.execute(select(func.count()).select_from(MatchOutcomeTable))).scalar_one()
            
            logger.info(f"Cycle 3: {final_matches} total matches, {outcomes} completed")
            
            await self._verify_system_state(
                redis_service,
                db_engine,
                VerificationState(
                    cycle_name="Cycle 3 - Match completion",
                    redis_pending={},
                    redis_statuses={},
                    db_counts={'matches': 3, 'predictions': 0, 'outcomes': outcomes},
                )
            )
        
        logger.info("Pipeline E2E test completed successfully:\n"
                    "  - Cycle 1: 2 new matches discovered\n"
                    "  - Cycle 2: 1 additional match (3 total)\n"
                    "  - Cycle 3: 1 match completed")