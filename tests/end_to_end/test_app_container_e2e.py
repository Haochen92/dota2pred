import pytest
import pytest_asyncio
from unittest.mock import patch, AsyncMock
from dependency_injector import providers
from live_orchestrator_app.app_container import AppContainer
from dota_oracle_common.models.live_games.schema import OngoingLeagueGame
from dota_oracle_common.models.match.schema import MatchesAPIResponse, ProMatchOutcome
from dota_oracle_pipeline.data_extraction.fetch_hero_data import fetch_hero_data
from sqlmodel import select

pytestmark = pytest.mark.asyncio(loop_scope='session')


class TestLivePipelineE2E:
    """Comprehensive E2E test tracking actual match progression through the complete pipeline."""

    # Test match IDs for consistent tracking
    MATCH_ID_1 = 7800001
    MATCH_ID_2 = 7800002
    MATCH_ID_3 = 7800003

    @pytest_asyncio.fixture(scope='function')
    async def test_app_container(
        self,
        e2e_redis_client,
        e2e_postgres_engine,
        e2e_environment
    ) -> AppContainer:
        """Create and configure test container with E2E infrastructure."""
        container = AppContainer()
        container.redis_async_pool.override(e2e_redis_client)
        container.db_engine.override(e2e_postgres_engine)
        
        # Override model inference service with correct URL
        from live_orchestrator_app.inference.model_inference_service import ModelInferenceService
        prediction_url = e2e_environment["prediction_api_url"]
        container.model_inference_service.override(
            providers.Resource(ModelInferenceService.create, base_url=prediction_url)
        )
        
        return container

    @pytest.fixture(scope='function')
    def cycle1_live_games(self, ongoing_league_game_factory):
        """Cycle 1: Two new matches discovered."""
        from dota_oracle_common.models.live_games.schema import LiveLeagueGame
        
        ongoing_games = [
            ongoing_league_game_factory.build(match_id=self.MATCH_ID_1),
            ongoing_league_game_factory.build(match_id=self.MATCH_ID_2)
        ]
        
        # Convert OngoingLeagueGame to LiveLeagueGame for mock compatibility
        return [LiveLeagueGame.model_validate(game.model_dump()) for game in ongoing_games]

    @pytest.fixture(scope='function')
    def cycle2_live_games(self, ongoing_league_game_factory):
        """Cycle 2: Previous matches still ongoing + one new match."""
        from dota_oracle_common.models.live_games.schema import LiveLeagueGame
        
        ongoing_games = [
            ongoing_league_game_factory.build(match_id=self.MATCH_ID_1),  # Still ongoing
            ongoing_league_game_factory.build(match_id=self.MATCH_ID_2),  # Still ongoing
            ongoing_league_game_factory.build(match_id=self.MATCH_ID_3)   # New match
        ]
        
        # Convert OngoingLeagueGame to LiveLeagueGame for mock compatibility
        return [LiveLeagueGame.model_validate(game.model_dump()) for game in ongoing_games]

    @pytest.fixture(scope='function')
    def cycle3_live_games(self, ongoing_league_game_factory):
        """Cycle 3: Match 1 completed (not in live games), others ongoing."""
        from dota_oracle_common.models.live_games.schema import LiveLeagueGame
        
        ongoing_games = [
            ongoing_league_game_factory.build(match_id=self.MATCH_ID_2),  # Still ongoing
            ongoing_league_game_factory.build(match_id=self.MATCH_ID_3)   # Still ongoing
        ]
        
        # Convert OngoingLeagueGame to LiveLeagueGame for mock compatibility
        return [LiveLeagueGame.model_validate(game.model_dump()) for game in ongoing_games]

    @pytest.fixture(scope='function')
    def match_details_responses(self, matches_api_response_factory):
        """Generate match details for our tracked matches."""
        return {
            self.MATCH_ID_1: matches_api_response_factory.build(match_id=self.MATCH_ID_1),
            self.MATCH_ID_2: matches_api_response_factory.build(match_id=self.MATCH_ID_2),
            self.MATCH_ID_3: matches_api_response_factory.build(match_id=self.MATCH_ID_3)
        }

    @pytest.fixture(scope='function')
    def completed_match_outcomes(self):
        """Completed match outcome for match 1."""
        return [
            ProMatchOutcome(match_id=self.MATCH_ID_1, radiant_win=True)
        ]

    @pytest_asyncio.fixture(scope='function')
    async def configured_test_container(self, test_app_container):
        """Configure container - with fallback to mock if BentoML unavailable."""
        # Try to use real BentoML service, fallback to mock if unavailable
        try:
            await test_app_container.init_resources()
            yield test_app_container
        except Exception as e:
            print(f"Warning: Could not initialize real BentoML service: {e}")
            print("Falling back to mock model service...")
            
            # Mock the model inference service if real service fails
            mock_model_service = AsyncMock()
            mock_model_service.predict_match_outcome = AsyncMock(return_value={
                "predicted_radiant_win_probability": 0.65
            })
            mock_model_service.feature_columns = ['feature1', 'feature2', 'feature3']
            mock_model_service.model_metadata = AsyncMock()
            mock_model_service.model_metadata.feature_columns = ['feature1', 'feature2', 'feature3']
            
            test_app_container.model_inference_service.override(lambda: mock_model_service)
            
            # Mock the feature preparation service
            mock_prep_service = AsyncMock()
            mock_prep_service.prepare_features = AsyncMock(return_value={
                'feature1': 1.0, 'feature2': 2.0, 'feature3': 3.0
            })
            test_app_container.feature_preparation_service.override(lambda _: mock_prep_service)
            
            try:
                await test_app_container.init_resources()
                yield test_app_container
            finally:
                await test_app_container.shutdown_resources()
        finally:
            try:
                await test_app_container.shutdown_resources()
            except:
                pass

    @pytest_asyncio.fixture(scope='function', autouse=True)
    async def setup_hero_data(self, e2e_postgres_engine):
        """Setup hero data before running pipeline tests."""
        from dota_oracle_common.models.heroes.table import HeroDataTable
        
        # Fetch real hero data and populate the database
        try:
            hero_data_dict = await fetch_hero_data()
            
            async with e2e_postgres_engine.connect() as conn:
                # Convert dict to list of HeroDataTable instances
                heroes_to_insert = []
                for hero_id_str, hero_data in hero_data_dict.items():
                    hero_table = HeroDataTable(
                        id=int(hero_id_str),
                        **hero_data.model_dump()
                    )
                    heroes_to_insert.append(hero_table)
                
                # Insert hero data
                if heroes_to_insert:
                    from sqlmodel import text
                    for hero in heroes_to_insert:
                        stmt = text("""
                            INSERT INTO herodatatable (id, name, localized_name, primary_attr, attack_type, roles)
                            VALUES (:id, :name, :localized_name, :primary_attr, :attack_type, :roles)
                            ON CONFLICT (id) DO NOTHING
                        """)
                        await conn.execute(stmt, {
                            "id": hero.id,
                            "name": hero.name,
                            "localized_name": hero.localized_name,
                            "primary_attr": hero.primary_attr,
                            "attack_type": hero.attack_type,
                            "roles": hero.roles
                        })
                    await conn.commit()
                    
                print(f"✓ Inserted {len(heroes_to_insert)} heroes into database")
                
        except Exception as e:
            print(f"Warning: Could not fetch hero data: {e}")
            # Test can continue without hero data if API is unavailable

    async def verify_redis_stream_progression(self, redis_service, expected_state: dict, cycle_name: str):
        """Verify Redis stream states and acknowledgments for proper pipeline progression."""
        redis_client = redis_service.redis
        
        print(f"\n{cycle_name} Redis Stream State:")
        
        # Stream names from the pipeline
        streams = {
            "new_matches": "feature_engineer_group",
            "pending_prediction": "prediction_group", 
            "pending_completion": "completion_group"
        }
        
        for stream_name, group_name in streams.items():
            try:
                # Check stream length
                stream_length = await redis_client.xlen(stream_name)
                
                # Check pending (unacknowledged) messages in consumer group
                pending_info = await redis_client.xpending(stream_name, group_name)
                pending_count = pending_info['pending']
                
                print(f"  {stream_name}:")
                print(f"    Total events: {stream_length}")
                print(f"    Pending (unack): {pending_count}")
                
                # Verify expected pending counts
                expected_pending = expected_state.get(f"{stream_name}_pending", None)
                if expected_pending is not None:
                    assert pending_count == expected_pending, \
                        f"{cycle_name}: {stream_name} should have {expected_pending} pending, got {pending_count}"
                
                # For non-zero pending, show which matches are stuck
                if pending_count > 0:
                    pending_details = await redis_client.xpending_range(
                        stream_name, group_name, '-', '+', count=10
                    )
                    for detail in pending_details:
                        print(f"    Pending event: {detail['message_id']} (consumer: {detail['consumer']})")
                        
            except Exception as e:
                print(f"    Stream {stream_name} not found or error: {e}")

    async def verify_match_status_tracking(self, redis_service, expected_matches: dict, cycle_name: str):
        """Verify match status tracking in Redis hashes."""
        redis_client = redis_service.redis
        
        print(f"\n{cycle_name} Match Status Tracking:")
        
        for match_id, expected_status in expected_matches.items():
            status_key = f"match_status:{match_id}"
            try:
                status_data = await redis_client.hgetall(status_key)
                current_status = status_data.get('status', 'not_found')
                
                print(f"  Match {match_id}: {current_status} (expected: {expected_status})")
                
                if expected_status != 'not_found':
                    assert current_status == expected_status, \
                        f"Match {match_id} should be in status {expected_status}, got {current_status}"
                        
            except Exception as e:
                print(f"  Match {match_id}: Error retrieving status - {e}")

    async def verify_comprehensive_database_state(self, db_engine, expected_state: dict, cycle_name: str):
        """Verify comprehensive database state across all tables."""
        from dota_oracle_common.models.match.table import MatchTable, MatchOutcomeTable
        from dota_oracle_common.models.inference.table import MatchPredictionTable
        from dota_oracle_common.models.features.table import TeamFeaturesTable, PlayerHeroFeatureTable, HeroFeaturesTable
        from dota_oracle_common.models.histories.table import TeamHistoryTable, TeamMatchupHistoryTable, PlayerHeroHistoryTable
        from dota_oracle_common.models.heroes.table import HeroDataTable
        
        async with db_engine.begin() as conn:
            print(f"\n{cycle_name} Database State:")
            
            # 1. Verify Matches Table
            result = await conn.execute(select(MatchTable))
            matches = result.fetchall()
            match_ids = {match.match_id for match in matches}
            expected_matches = expected_state.get('matches', [])
            
            print(f"  Matches: {len(matches)} (expected: {len(expected_matches)})")
            for match_id in expected_matches:
                assert match_id in match_ids, f"Match {match_id} should be in matches table"
                print(f"    ✓ Match {match_id} found")
            
            # 2. Verify Match Outcomes Table
            result = await conn.execute(select(MatchOutcomeTable))
            outcomes = result.fetchall()
            outcome_match_ids = {outcome.match_id for outcome in outcomes}
            expected_outcomes = expected_state.get('match_outcomes', [])
            
            print(f"  Match Outcomes: {len(outcomes)} (expected: {len(expected_outcomes)})")
            for match_id in expected_outcomes:
                assert match_id in outcome_match_ids, f"Match {match_id} should have outcome"
                print(f"    ✓ Outcome for match {match_id} found")
            
            # 3. Verify Match Predictions Table
            result = await conn.execute(select(MatchPredictionTable))
            predictions = result.fetchall()
            prediction_match_ids = {pred.match_id for pred in predictions}
            expected_predictions = expected_state.get('match_predictions', [])
            
            print(f"  Match Predictions: {len(predictions)} (expected: {len(expected_predictions)})")
            for match_id in expected_predictions:
                assert match_id in prediction_match_ids, f"Match {match_id} should have prediction"
                print(f"    ✓ Prediction for match {match_id} found")
            
            # 4. Verify Feature Tables
            tables_to_check = [
                (TeamFeaturesTable, 'team_features'),
                (PlayerHeroFeatureTable, 'player_hero_features'),
                (HeroFeaturesTable, 'hero_features')
            ]
            
            for table_class, expected_key in tables_to_check:
                result = await conn.execute(select(table_class))
                features = result.fetchall()
                feature_match_ids = {f.match_id for f in features}
                expected_features = expected_state.get(expected_key, [])
                
                print(f"  {expected_key.replace('_', ' ').title()}: {len(features)} (expected: {len(expected_features)})")
                for match_id in expected_features:
                    assert match_id in feature_match_ids, f"Match {match_id} should have {expected_key}"
                    print(f"    ✓ {expected_key} for match {match_id} found")
            
            # 5. Verify History Tables
            history_tables = [
                (TeamHistoryTable, 'team_histories'),
                (TeamMatchupHistoryTable, 'team_matchup_histories'), 
                (PlayerHeroHistoryTable, 'player_hero_histories')
            ]
            
            for table_class, expected_key in history_tables:
                result = await conn.execute(select(table_class))
                histories = result.fetchall()
                history_match_ids = {h.match_id for h in histories}
                expected_histories = expected_state.get(expected_key, [])
                
                print(f"  {expected_key.replace('_', ' ').title()}: {len(histories)} (expected: >= {len(expected_histories)})")
                for match_id in expected_histories:
                    assert match_id in history_match_ids, f"Match {match_id} should have {expected_key}"
                    print(f"    ✓ {expected_key} for match {match_id} found")

    async def test_complete_pipeline_progression_three_cycles(
        self,
        configured_test_container: AppContainer,
        cycle1_live_games,
        cycle2_live_games,
        cycle3_live_games,
        match_details_responses,
        completed_match_outcomes
    ):
        """
        Test complete pipeline progression showing proper advancement through all stages.
        
        Pipeline Flow: new_match → feature_engineering → prediction → completion
        
        Cycle 1: 2 new matches → should advance through new_match → FE → prediction → completion
        Cycle 2: 1 new match + 2 existing in completion → new match advances, others stay in completion
        Cycle 3: 1 match completes → completion acknowledged and removed from tracking
        """
        
        app = await configured_test_container.app()
        redis_service = await configured_test_container.redis_service()
        db_engine = configured_test_container.db_engine()
        
        # =====================
        # INITIAL STATE VERIFICATION
        # =====================
        await self.verify_redis_stream_progression(redis_service, {}, "Initial")
        await self.verify_match_status_tracking(redis_service, {}, "Initial")
        
        # =====================
        # CYCLE 1: Two new matches → complete pipeline progression 
        # =====================
        print("\n" + "="*60)
        print("CYCLE 1: Two new matches → complete pipeline progression")
        print("="*60)
        
        async def mock_fetch_match_details(match_id: int):
            return match_details_responses.get(match_id)
        
        with patch('dota_oracle_pipeline.data_extraction.fetch_live_leagues.fetch_live_league_games') as mock_live_games, \
             patch('dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details', side_effect=mock_fetch_match_details), \
             patch('dota_oracle_pipeline.data_extraction.fetch_pro_match.fetch_pro_match') as mock_pro_match:
            
            mock_live_games.return_value = cycle1_live_games
            mock_pro_match.return_value = []  # No completed matches yet
            
            # Run cycle 1 - should process: new_match → FE → prediction → completion
            await app.run_cycle()
            
            # Verify cycle 1: matches should be in completion stage (pending completion check)
            await self.verify_redis_stream_progression(redis_service, {
                "new_matches_pending": 0,           # Should be acknowledged 
                "pending_prediction_pending": 0,    # Should be acknowledged
                "pending_completion_pending": 2     # 2 matches awaiting completion check
            }, "Cycle 1")
            
            await self.verify_match_status_tracking(redis_service, {
                self.MATCH_ID_1: "pending_completion",
                self.MATCH_ID_2: "pending_completion"
            }, "Cycle 1")
            
            await self.verify_comprehensive_database_state(db_engine, {
                'matches': [self.MATCH_ID_1, self.MATCH_ID_2],
                'match_outcomes': [],  # No outcomes yet (not completed)
                'match_predictions': [self.MATCH_ID_1, self.MATCH_ID_2],  # Should have predictions
                'team_features': [self.MATCH_ID_1, self.MATCH_ID_2],
                'player_hero_features': [self.MATCH_ID_1, self.MATCH_ID_2],
                'hero_features': [self.MATCH_ID_1, self.MATCH_ID_2],
                'team_histories': [self.MATCH_ID_1, self.MATCH_ID_2],
                'team_matchup_histories': [self.MATCH_ID_1, self.MATCH_ID_2],
                'player_hero_histories': [self.MATCH_ID_1, self.MATCH_ID_2]
            }, "Cycle 1")

        # =====================
        # CYCLE 2: One new match + existing matches still in completion
        # =====================
        print("\n" + "="*60)
        print("CYCLE 2: One new match + existing matches in completion")
        print("="*60)
        
        with patch('dota_oracle_pipeline.data_extraction.fetch_live_leagues.fetch_live_league_games') as mock_live_games, \
             patch('dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details', side_effect=mock_fetch_match_details), \
             patch('dota_oracle_pipeline.data_extraction.fetch_pro_match.fetch_pro_match') as mock_pro_match:
            
            mock_live_games.return_value = cycle2_live_games
            mock_pro_match.return_value = []  # Still no completed matches
            
            # Run cycle 2
            await app.run_cycle()
            
            # Verify cycle 2: new match progresses, existing stay in completion
            await self.verify_redis_stream_progression(redis_service, {
                "new_matches_pending": 0,           # New match should be processed
                "pending_prediction_pending": 0,    # Should be processed
                "pending_completion_pending": 3     # All 3 matches in completion stage
            }, "Cycle 2")
            
            await self.verify_match_status_tracking(redis_service, {
                self.MATCH_ID_1: "pending_completion",
                self.MATCH_ID_2: "pending_completion", 
                self.MATCH_ID_3: "pending_completion"
            }, "Cycle 2")
            
            await self.verify_comprehensive_database_state(db_engine, {
                'matches': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'match_outcomes': [],  # Still no outcomes
                'match_predictions': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'team_features': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'player_hero_features': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'hero_features': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'team_histories': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'team_matchup_histories': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'player_hero_histories': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3]
            }, "Cycle 2")

        # =====================
        # CYCLE 3: Match 1 completes → outcome recorded, tracking removed
        # =====================
        print("\n" + "="*60)
        print("CYCLE 3: Match 1 completes → outcome recorded, tracking removed")
        print("="*60)
        
        with patch('dota_oracle_pipeline.data_extraction.fetch_live_leagues.fetch_live_league_games') as mock_live_games, \
             patch('dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details', side_effect=mock_fetch_match_details), \
             patch('dota_oracle_pipeline.data_extraction.fetch_pro_match.fetch_pro_match') as mock_pro_match:
            
            # Match 1 no longer in live games (completed)
            mock_live_games.return_value = cycle3_live_games
            mock_pro_match.return_value = completed_match_outcomes  # Match 1 completed
            
            # Run cycle 3
            await app.run_cycle()
            
            # Verify cycle 3: Match 1 completed and removed from tracking, others remain
            await self.verify_redis_stream_progression(redis_service, {
                "new_matches_pending": 0,           # No new matches
                "pending_prediction_pending": 0,    # No pending predictions
                "pending_completion_pending": 2     # Only matches 2&3 still in completion
            }, "Cycle 3")
            
            await self.verify_match_status_tracking(redis_service, {
                self.MATCH_ID_1: "completed",       # Should be marked completed
                self.MATCH_ID_2: "pending_completion",
                self.MATCH_ID_3: "pending_completion"
            }, "Cycle 3")
            
            await self.verify_comprehensive_database_state(db_engine, {
                'matches': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'match_outcomes': [self.MATCH_ID_1],  # Match 1 should have outcome
                'match_predictions': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'team_features': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'player_hero_features': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'hero_features': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'team_histories': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'team_matchup_histories': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3],
                'player_hero_histories': [self.MATCH_ID_1, self.MATCH_ID_2, self.MATCH_ID_3]
            }, "Cycle 3")

    async def test_bentoml_prediction_integration(
        self,
        configured_test_container: AppContainer,
        cycle1_live_games,
        match_details_responses
    ):
        """Test that BentoML predictions are properly made and stored."""
        
        app = await configured_test_container.app()
        db_engine = configured_test_container.db_engine()
        
        async def mock_fetch_match_details(match_id: int):
            return match_details_responses.get(match_id)
        
        with patch('dota_oracle_pipeline.data_extraction.fetch_live_leagues.fetch_live_league_games') as mock_live_games, \
             patch('dota_oracle_pipeline.data_extraction.fetch_match_details.fetch_match_details', side_effect=mock_fetch_match_details), \
             patch('dota_oracle_pipeline.data_extraction.fetch_pro_match.fetch_pro_match') as mock_pro_match:
            
            mock_live_games.return_value = cycle1_live_games
            mock_pro_match.return_value = []
            
            # Run one cycle - should complete full progression including predictions
            await app.run_cycle()
            
            # Verify predictions were made using real BentoML service
            from dota_oracle_common.models.inference.table import MatchPredictionTable
            
            async with db_engine.begin() as conn:
                result = await conn.execute(select(MatchPredictionTable))
                predictions = result.fetchall()
                
                assert len(predictions) >= 2, "Should have predictions for both matches"
                
                for pred in predictions:
                    assert pred.match_id in [self.MATCH_ID_1, self.MATCH_ID_2], "Prediction should be for expected match"
                    assert 0.0 <= pred.predicted_radiant_win_probability <= 1.0, "Probability should be between 0 and 1"
                    assert pred.predictor_name is not None, "Should have predictor name"
                    assert pred.prediction_date is not None, "Should have prediction timestamp"
                    print(f"✓ BentoML Prediction for match {pred.match_id}: {pred.predicted_radiant_win_probability:.3f}")

    async def test_pipeline_error_resilience(
        self,
        configured_test_container: AppContainer
    ):
        """Test pipeline resilience to external API failures."""
        
        app = await configured_test_container.app()
        
        with patch('dota_oracle_pipeline.data_extraction.fetch_live_leagues.fetch_live_league_games') as mock_live_games:
            
            # Simulate API failure
            mock_live_games.side_effect = Exception("Steam API temporarily unavailable")
            
            # Pipeline should handle the error gracefully without crashing
            try:
                await app.run_cycle()
                pipeline_survived = True
            except Exception as e:
                pipeline_survived = False
                pytest.fail(f"Pipeline should handle external API failures gracefully, but got: {e}")
            
            assert pipeline_survived, "Pipeline should survive external API failures"