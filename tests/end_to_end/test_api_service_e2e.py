import pytest
import pytest_asyncio
import asyncio
import json
import httpx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.api import PublicMatchPredictionRequest, PublicMatchPredictionResponse
from tests.factories.api_service_factory import LiveStateUpdateRequestFactory

# Import the actual table models and factories
from dota_oracle_common.models.match import MatchTable, MatchOutcomeTable
from dota_oracle_common.models.inference.table import MatchPredictionTable
from tests.factories.repository_factories import (
    MatchTableFactory,
    MatchOutcomeTableFactory,
    MatchPredictionTableFactory,
)

logger = get_logger(__name__)
# This mark applies to all tests in this file
pytestmark = [pytest.mark.asyncio(loop_scope="session"), pytest.mark.e2e]


# =================================================================================
# TESTS FOR THE /inference ROUTER
# =================================================================================
# =================================================================================
# TESTS FOR THE /inference ROUTER
# =================================================================================
class TestInferenceRouterE2E:
    """End-to-end tests for the /inference router."""

    async def test_prediction_happy_path(
        self,
        full_stack_client: AsyncClient,
    ):
        """Tests the /inference/predict endpoint with a valid request."""
        logger.info("Testing inference endpoint happy path...")

        valid_request = PublicMatchPredictionRequest(
            radiant_heroes=[1, 2, 3, 4, 5],
            dire_heroes=[6, 7, 8, 9, 10],
        )

        response = await full_stack_client.post("/inference/predict", json=valid_request.model_dump())

        assert response.status_code == 200
        response_data = response.json()

        # Validate response schema
        PublicMatchPredictionResponse.model_validate(response_data)

        assert "prediction" in response_data
        assert "probability" in response_data
        if response_data["probability"] is not None:
            assert 0.0 <= response_data["probability"] <= 1.0

        logger.info(f"Prediction successful with response: {response_data}")

    async def test_prediction_with_duplicate_heroes(
        self,
        full_stack_client: AsyncClient,
    ):
        """Tests the /inference/predict endpoint rejects duplicate heroes."""
        logger.info("Testing inference endpoint with duplicate heroes...")

        # Send raw dict to let FastAPI/Pydantic handle validation
        invalid_request_data = {
            "radiant_heroes": [1, 2, 3, 4, 5],
            "dire_heroes": [1, 7, 8, 9, 10],  # Duplicate Anti-Mage across sides
        }

        response = await full_stack_client.post("/inference/predict", json=invalid_request_data)

        assert response.status_code == 422
        response_data = response.json()
        logger.info(f"Validation error response: {response_data}")

        # FastAPI returns validation errors as a list of error objects
        error_detail = str(response_data["detail"]).lower()
        assert "duplicate" in error_detail
        logger.info("Correctly rejected duplicate heroes with 422 error.")


# =================================================================================
# TESTS FOR THE /matches ROUTER
# =================================================================================
class TestMatchesRouterE2E:
    """End-to-end tests for the /matches router with factory-generated test data."""

    @pytest_asyncio.fixture(scope="function")
    async def seed_test_matches(self, e2e_postgres_engine):
        """Seeds the database with controlled match data using factories."""
        logger.info("Seeding database with test match data...")

        # Create match 1 using factory
        match1 = MatchTableFactory.build(
            match_id=1001,
            duration=1800.0,
            patch="7.32",
            radiant_team_id=1,
            dire_team_id=2,
            slot_0_hero_id=1,  # Anti-Mage
            slot_1_hero_id=2,  # Axe
            slot_2_hero_id=3,  # Bane
            slot_3_hero_id=4,  # Bloodseeker
            slot_4_hero_id=5,  # Crystal Maiden
            slot_128_hero_id=6,
            slot_129_hero_id=7,
            slot_130_hero_id=8,
            slot_131_hero_id=9,
            slot_132_hero_id=10,
        )

        match1_outcome = MatchOutcomeTableFactory.build(match_id=1001, radiant_win=True)

        # Create match 2 using factory
        match2 = MatchTableFactory.build(
            match_id=1002,
            duration=2400.0,
            patch="7.33",
            radiant_team_id=3,
            dire_team_id=4,
            slot_0_hero_id=11,
            slot_1_hero_id=12,
            slot_2_hero_id=13,
            slot_3_hero_id=14,
            slot_4_hero_id=15,
            slot_128_hero_id=16,
            slot_129_hero_id=17,
            slot_130_hero_id=1,
            slot_131_hero_id=18,  # Anti-Mage in dire
            slot_132_hero_id=19,
        )

        match2_outcome = MatchOutcomeTableFactory.build(match_id=1002, radiant_win=False)

        # Create predictions for both matches
        match1_prediction = MatchPredictionTableFactory.build(
            match_id=1001, prediction=True, predictor_name="test_predictor"  # Predicted radiant win
        )

        match2_prediction = MatchPredictionTableFactory.build(
            match_id=1002, prediction=False, predictor_name="test_predictor"  # Predicted dire win
        )

        # Insert test data
        async with async_sessionmaker(bind=e2e_postgres_engine)() as session:
            async with session.begin():
                session.add_all([match1, match2])
                session.add_all([match1_outcome, match2_outcome])
                session.add_all([match1_prediction, match2_prediction])
            await session.commit()

        logger.info("Seeded 2 test matches with outcomes.")

        yield {"match1_id": 1001, "match2_id": 1002}

        # Cleanup: Delete the test matches
        logger.info("Cleaning up seeded test matches...")
        from sqlalchemy import delete

        async with async_sessionmaker(bind=e2e_postgres_engine)() as session:
            async with session.begin():
                # Delete predictions first
                await session.execute(
                    delete(MatchPredictionTable).where(MatchPredictionTable.match_id.in_([1001, 1002]))
                )
                # Delete match outcomes (foreign key constraint)
                await session.execute(delete(MatchOutcomeTable).where(MatchOutcomeTable.match_id.in_([1001, 1002])))
                # Delete matches
                await session.execute(delete(MatchTable).where(MatchTable.match_id.in_([1001, 1002])))
            await session.commit()
        logger.info("Test matches cleanup completed.")

    async def test_get_matches_no_filters(self, full_stack_client: AsyncClient, seed_test_matches):
        """Tests fetching matches without any filters."""
        logger.info("Testing GET /matches without filters...")
        response = await full_stack_client.get("/matches/")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2
        assert len(data["matches"]) == 2
        # Should be ordered by match_id DESC (latest first)
        assert data["matches"][0]["match_id"] == seed_test_matches["match2_id"]
        logger.info("Successfully fetched all 2 seeded matches.")

    async def test_get_matches_filter_by_hero(self, full_stack_client: AsyncClient, seed_test_matches):
        """Tests filtering matches by hero name."""
        logger.info("Testing GET /matches with hero filter...")
        response = await full_stack_client.get("/matches/?hero_name=Anti-Mage")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 2  # Anti-Mage in both matches
        logger.info("Successfully filtered matches for 'Anti-Mage'.")

    async def test_get_matches_pagination(self, full_stack_client: AsyncClient, seed_test_matches):
        """Tests pagination functionality."""
        logger.info("Testing GET /matches pagination...")
        response = await full_stack_client.get("/matches/?page=2&page_size=1")

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert len(data["matches"]) == 1
        assert data["matches"][0]["match_id"] == seed_test_matches["match1_id"]  # Second match (oldest)
        logger.info("Pagination test successful.")


# =================================================================================
# TESTS FOR THE /streaming ROUTER
# =================================================================================
class TestStreamingRouterE2E:
    """End-to-end tests for the /streaming router."""

    @pytest.fixture(scope="class")
    def streaming_timeout(self) -> httpx.Timeout:
        """Provides timeout for SSE connections."""
        return httpx.Timeout(10.0, read=30.0)

    async def test_live_update_endpoint(self, full_stack_client: AsyncClient):
        """Tests the live state update endpoint."""
        logger.info("Testing POST /streaming/live-state-update...")

        live_update_payload = LiveStateUpdateRequestFactory.build()

        response = await full_stack_client.post(
            "/streaming/live-state-update", json=live_update_payload.model_dump(mode="json")
        )

        assert response.status_code == 202
        response_data = response.json()
        assert "status" in response_data and response_data["status"] == "success"
        logger.info("Live state update endpoint working correctly.")

    @pytest.mark.skip(reason="SSE + in-process ASGI transport can hang; skip in CI")
    async def test_sse_endpoint_connection(self, full_stack_client: AsyncClient, streaming_timeout: httpx.Timeout):
        """Tests that an SSE client can connect and receive the initial handshake."""
        async with full_stack_client.stream(
            "GET", "/streaming/sse/live_matches", timeout=streaming_timeout
        ) as response:
            response.raise_for_status()
            assert "text/event-stream" in response.headers.get("content-type", "")

            initial_line = await anext(response.aiter_lines())
            assert initial_line == ": connected"

    @pytest.mark.skip(reason="SSE + in-process ASGI transport can hang; skip in CI")
    async def test_sse_pubsub_flow(self, full_stack_client: AsyncClient, streaming_timeout: httpx.Timeout):
        """
        Tests the full pub/sub flow sequentially with an explicit timeout.
        """
        logger.info("Testing full sequential SSE pub/sub flow...")
        live_update_payload = LiveStateUpdateRequestFactory.build()
        expected_python_dict = live_update_payload.model_dump(mode="json")
        received_data = None

        try:
            async with full_stack_client.stream(
                "GET", "/streaming/sse/live_matches", timeout=streaming_timeout
            ) as response:
                response.raise_for_status()
                line_iterator = response.aiter_lines()

                handshake = await anext(line_iterator)
                assert handshake == ": connected"
                logger.info("SSE Handshake received.")

                await asyncio.sleep(0.1)  # Still needed to prevent race condition
                publish_response = await full_stack_client.post(
                    "/streaming/live-state-update", json=live_update_payload.model_dump(mode="json")
                )
                assert publish_response.status_code == 202
                logger.info("Published update to trigger SSE event.")

                while True:
                    line = await anext(line_iterator)
                    logger.info(f"Received SSE line: '{line}'")
                    if line.startswith("data: "):
                        received_data = line[len("data: ") :].strip()
                        break
        except httpx.ReadTimeout:
            pytest.fail("Test timed out while waiting for SSE message after publishing.")

        assert received_data is not None, "Did not receive any data from the SSE stream."
        assert json.loads(received_data) == expected_python_dict
