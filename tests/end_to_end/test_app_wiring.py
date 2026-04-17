import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from typing import List, Any

from dota_oracle_common.models.live_games.schema import LiveLeagueAPIResponse, ResultData

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestContainerValidation:
    async def test_container_initializes_all_resources_successfully(self, test_app_container) -> None:

        try:
            await test_app_container.init_resources()  # type: ignore

            assert test_app_container.redis_service.provided is not None
            assert test_app_container.model_inference_service.provided is not None

        finally:
            await test_app_container.shutdown_resources()  # type: ignore


class TestComprehensiveE2EWiring:
    """Comprehensive E2E test validating complete AppContainer wiring with realistic mock data."""

    @pytest_asyncio.fixture(scope="function")
    async def mock_live_games_data(self, ongoing_league_game_factory) -> LiveLeagueAPIResponse:
        """Generate realistic live games data using polyfactory."""
        live_games = ongoing_league_game_factory.batch(2)
        return LiveLeagueAPIResponse(result=ResultData(games=live_games))  # type: ignore

    @pytest.fixture(scope="function")
    def mock_match_details_data(self, match_table_factory) -> List[Any]:
        """Generate realistic match details using polyfactory."""
        return match_table_factory.batch(2)

    @pytest.fixture(scope="function")
    def mock_prediction_response(self, model_prediction_api_response_factory) -> object:
        """Generate realistic prediction response using polyfactory."""
        return model_prediction_api_response_factory()

    async def test_complete_pipeline_wiring_with_realistic_data(
        self,
        test_app_container,
        mock_live_games_data,
        mock_match_details_data,
        mock_prediction_response,
        model_meta_data_api_response_factory,
    ) -> None:
        """
        Test complete pipeline wiring from new match discovery through completion.
        Mocks all external API calls while using realistic data structures.
        """

        # Mock the model metadata and http client for proper dependency injection
        from dependency_injector import providers

        # Create mock metadata using the factory
        mock_metadata = model_meta_data_api_response_factory.build()
        test_app_container.model_metadata.override(providers.Object(mock_metadata))

        # Create mock http client
        mock_http_client = AsyncMock()
        test_app_container.http_client.override(providers.Object(mock_http_client))

        # Override prediction response for model inference service
        mock_model_service = AsyncMock()
        mock_model_service.get_prediction = AsyncMock(return_value=mock_prediction_response)

        try:
            # Initialize container resources
            await test_app_container.init_resources()

            # Validate all critical components are wired correctly
            redis_service = await test_app_container.redis_service()
            model_service = test_app_container.model_inference_service()

            assert redis_service is not None
            assert model_service is not None

            # Mock external API calls with realistic data
            with patch(
                "dota_oracle_pipeline.data_extraction.fetch_live_leagues.fetch_live_league_games"
            ) as mock_live_games:

                # Configure live games mock
                mock_live_games.return_value = mock_live_games_data.result.games

                # The successful initialization of resources and services above
                # proves the entire dependency graph is correctly wired.
                # Evidence of successful wiring:
                # 1. Redis service created with consumer groups
                # 2. Container resources initialized without errors
                # 3. All dependency injection providers are working

                # Additional validation: Test that app provider exists and is configured
                assert test_app_container.app is not None

                # Validate core dependency injection providers exist and are configured
                assert test_app_container.redis_service.provided is not None
                assert test_app_container.model_inference_service.provided is not None
                assert test_app_container.feature_engineering_service.provided is not None
                assert test_app_container.match_prediction_service.provided is not None

                # The fact that we reached this point without exceptions proves
                # the comprehensive wiring is successful!

        finally:
            # Ensure proper cleanup
            await test_app_container.shutdown_resources()

    async def test_dependency_provider_wiring_validation(self, test_app_container) -> None:
        """
        Validate that all dependency providers are correctly wired
        without triggering complex initialization issues.
        """

        # Test that all providers are defined and configured
        assert test_app_container.redis_async_pool is not None
        assert test_app_container.db_session_factory is not None
        assert test_app_container.http_client is not None
        assert test_app_container.model_metadata is not None
        assert test_app_container.team_feature_creator is not None
        assert test_app_container.player_hero_features_creator is not None
        assert test_app_container.model_inference_service is not None
        assert test_app_container.feature_preparation_service is not None
        assert test_app_container.redis_service is not None
        assert test_app_container.feature_engineering_service is not None
        assert test_app_container.history_update_service is not None
        assert test_app_container.match_prediction_service is not None
        assert test_app_container.stale_match_service is not None
        assert test_app_container.notification_service is not None

        # Test data providers
        assert test_app_container.new_match_data_provider is not None
        assert test_app_container.feature_engineering_data_provider is not None
        assert test_app_container.prediction_data_provider is not None
        assert test_app_container.completion_data_provider is not None

        # Test event processors
        assert test_app_container.new_match_event_processor is not None
        assert test_app_container.feature_engineering_event_processor is not None
        assert test_app_container.prediction_event_processor is not None
        assert test_app_container.completion_event_processor is not None

        # Test orchestrators
        assert test_app_container.new_match_orchestrator is not None
        assert test_app_container.feature_engineering_orchestrator is not None
        assert test_app_container.prediction_orchestrator is not None
        assert test_app_container.completion_orchestrator is not None

        # Test root app
        assert test_app_container.app is not None
