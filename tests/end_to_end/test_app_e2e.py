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

from dota_oracle_common.models.live_games.schema import ScoreBoard, Faction, Player, TeamData
import random

logger = logging.getLogger(__name__)
pytestmark = [pytest.mark.asyncio(loop_scope='session'), pytest.mark.e2e]


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
    RADIANT_SLOT_IDS = list(range(5))
    DIRE_SLOT_IDS = list(range(128, 133))

    @pytest.fixture(scope='function')
    def live_league_data(self, ongoing_league_game_factory, player_factory) -> Dict[int, OngoingLeagueGame]:
        
        matches = {}
        for match_id in self.MATCH_IDS:
            match = ongoing_league_game_factory.build(match_id=match_id)
            
            # Override player and hero slot values to reflect true data
            # Use well-known valid hero IDs from Dota 2
            # Anti-Mage=1, Axe=2, Bane=3, Bloodseeker=4, Crystal Maiden=5
            # Drow Ranger=6, Earthshaker=7, Juggernaut=8, Mirana=9, Pudge=14
            radiant_hero_ids = [1, 2, 3, 4, 5]  # Anti-Mage, Axe, Bane, Bloodseeker, Crystal Maiden
            dire_hero_ids = [6, 7, 8, 9, 14]    # Drow Ranger, Earthshaker, Juggernaut, Mirana, Pudge
            
            match.scoreboard.radiant.players = [
                player_factory.build(
                    player_slot=i,
                    account_id=i + 2000,
                    hero_id=radiant_hero_ids[i],
                    name=f"player_{i}"
                ) for i in self.RADIANT_SLOT_IDS
            ]
            match.scoreboard.dire.players = [
                player_factory.build(
                    player_slot=i,
                    account_id=i + 2000,
                    hero_id=dire_hero_ids[i - 128],
                    name=f"player_{i}"
                ) for i in self.DIRE_SLOT_IDS
            ]
            
            matches[match_id] = match
            
        return matches

    @pytest.fixture(scope='function')
    def match_details_fetcher(self, matches_api_response_factory, player_data_factory) -> Callable[[int], Optional[MatchesAPIResponse]]:
        """Mock match details provider."""
        
        details_map = {}
        for match_id in self.MATCH_IDS:
            response = matches_api_response_factory.build(match_id=match_id)
            # Use the same hero IDs as the live data
            radiant_hero_ids = [1, 2, 3, 4, 5]  # Anti-Mage, Axe, Bane, Bloodseeker, Crystal Maiden
            dire_hero_ids = [6, 7, 8, 9, 14]    # Drow Ranger, Earthshaker, Juggernaut, Mirana, Pudge
            all_slots = self.RADIANT_SLOT_IDS + self.DIRE_SLOT_IDS
            
            response.players = [
                player_data_factory.build(
                    player_slot=i,
                    account_id=i+2000,
                    hero_id=radiant_hero_ids[i] if i < 5 else dire_hero_ids[i - 128],
                    name=f"player_{i}"
                ) for i in all_slots
            ]
            details_map[match_id] = response
            
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

    async def _verify_system_state(self, redis_service, db_engine, expected: VerificationState):
        """A single, clean entry point to verify the entire system state."""
        logger.info(f"--- Verifying State for: {expected.cycle_name} ---")
        await self._verify_redis_streams(redis_service, expected.redis_pending, expected.cycle_name)
        await self._verify_match_statuses(redis_service, expected.redis_statuses, expected.cycle_name)
        await self._verify_db_counts(db_engine, expected.db_counts, expected.cycle_name)
        logger.info(f"--- State for {expected.cycle_name} verified successfully. ---")
        
    async def _verify_redis_streams(self, redis_service, expected_pending: Dict[str, int], cycle: str):
        streams = ["new_matches", "pending_prediction", "pending_completion"]
        for stream in streams:
            group = f"{stream}_group"
            try:
                pending_info = await redis_service.redis.xpending(stream, group)
                actual = pending_info['pending']
            except Exception:
                actual = 0
            expected = expected_pending.get(stream, 0)
            assert actual == expected, f"[{cycle}] Stream '{stream}' has {actual} pending, expected {expected}"

    async def _verify_match_statuses(self, redis_service, expected_statuses: Dict[int, str], cycle: str):
        for match_id, expected_status in expected_statuses.items():
            status = await redis_service.get_match_status(match_id)
            assert status == expected_status, f"[{cycle}] Match {match_id} status is '{status}', expected '{expected_status}'"

    async def _verify_db_counts(self, db_engine, expected_counts: Dict[str, int], cycle: str):
        table_map = {'matches': MatchTable, 'predictions': MatchPredictionTable, 'outcomes': MatchOutcomeTable}
        async with db_engine.begin() as conn:
            for key, table in table_map.items():
                # Use `table.match_id` for counting to handle potential empty tables
                count = await conn.scalar(select(func.count(table.match_id)))
                expected = expected_counts.get(key, 0)
                assert count == expected, f"[{cycle}] Table '{table.__tablename__}' has {count} rows, expected {expected}"

    # --- E2E Test Cases (Sequential and Dependent) ---

    async def test_initial_state(self, configured_test_container: AppContainer, setup_hero_data):
        """Verify that the system starts in a clean, empty state."""
        redis_service = await configured_test_container.redis_service()
        db_engine = configured_test_container.db_engine()
        await self._verify_system_state(
            redis_service, db_engine, VerificationState(cycle_name="Initial State")
        )

    @pytest.mark.dependency(depends=['test_initial_state'])
    async def test_cycle_1_new_match_discovery(
        self, configured_test_container: AppContainer, cycle1_live_games, match_details_fetcher, setup_hero_data
    ):
        """CYCLE 1: Tests the discovery and full processing of two new matches."""
        app = await configured_test_container.app()
        redis_service = await configured_test_container.redis_service()
        db_engine = configured_test_container.db_engine()

        # ARRANGE
        with patch("live_orchestrator_app.data_fetching.new_match_data_provider.fetch_live_league_games", return_value=cycle1_live_games), \
             patch("dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details", side_effect=match_details_fetcher), \
             patch("live_orchestrator_app.services.fetch_outcome_service.fetch_pro_match", return_value=[]):
            
            # ACT: Run the pipeline
            await app.run_cycle()

        # ASSERT: Verify the system state after processing two new matches.
        await self._verify_system_state(redis_service, db_engine, VerificationState(
            cycle_name="Cycle 1 - Two New Matches",
            redis_pending={"pending_completion": 2},
            redis_statuses={self.MATCH_IDS[0]: "pending_completion", self.MATCH_IDS[1]: "pending_completion"},
            db_counts={'matches': 2, 'predictions': 2, 'outcomes': 0},
        ))

    @pytest.mark.dependency(depends=['test_cycle_1_new_match_discovery'])
    async def test_cycle_2_additional_match(
        self, configured_test_container: AppContainer, cycle2_live_games, match_details_fetcher, setup_hero_data
    ):
        """CYCLE 2: Tests discovery of one new match while others are pending."""
        app = await configured_test_container.app()
        redis_service = await configured_test_container.redis_service()
        db_engine = configured_test_container.db_engine()

        with patch("live_orchestrator_app.data_fetching.new_match_data_provider.fetch_live_league_games", return_value=cycle2_live_games), \
             patch("dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details", side_effect=match_details_fetcher), \
             patch("live_orchestrator_app.services.fetch_outcome_service.fetch_pro_match", return_value=[]):

            await app.run_cycle()

        await self._verify_system_state(redis_service, db_engine, VerificationState(
            cycle_name="Cycle 2 - One Additional Match",
            redis_pending={"pending_completion": 3},
            redis_statuses={mid: "pending_completion" for mid in self.MATCH_IDS},
            db_counts={'matches': 3, 'predictions': 3, 'outcomes': 0},
        ))

    @pytest.mark.dependency(depends=['test_cycle_2_additional_match'])
    async def test_cycle_3_match_completion(
        self, configured_test_container: AppContainer, cycle3_live_games, completed_match_outcomes, setup_hero_data
    ):
        """CYCLE 3: Tests the completion of one match and its state removal from pending."""
        app = await configured_test_container.app()
        redis_service = await configured_test_container.redis_service()
        db_engine = configured_test_container.db_engine()

        with patch("live_orchestrator_app.data_fetching.new_match_data_provider.fetch_live_league_games", return_value=cycle3_live_games), \
             patch("live_orchestrator_app.services.fetch_outcome_service.fetch_pro_match", return_value=completed_match_outcomes):

            await app.run_cycle()

        await self._verify_system_state(redis_service, db_engine, VerificationState(
            cycle_name="Cycle 3 - Match Completion",
            redis_pending={"pending_completion": 2},
            redis_statuses={
                self.MATCH_IDS[0]: "completed",
                self.MATCH_IDS[1]: "pending_completion",
                self.MATCH_IDS[2]: "pending_completion"
            },
            db_counts={'matches': 3, 'predictions': 3, 'outcomes': 1},
        ))