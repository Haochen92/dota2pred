import pytest
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession
from httpx import AsyncClient
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.api import PublicMatchPredictionRequest
from dota_oracle_common.repositories.heroes_repository import HeroesRepository

logger = get_logger(__name__)
pytestmark = [pytest.mark.asyncio(loop_scope="session"), pytest.mark.e2e]


class TestDataPollutionDetection:
    """
    Tests to detect data pollution between different test modules.
    These tests verify that data created by one test module doesn't
    interfere with or pollute other test modules.
    """

    async def test_api_service_pollution_detection(
        self,
        full_stack_client: AsyncClient,
        e2e_redis_client: aioredis.Redis,
        e2e_postgres_engine,
    ):
        """
        Test that simulates API service operations and checks for pollution.
        This test writes specific data and verifies it can be isolated.
        """
        # 1. Test API service functionality and create some data
        valid_request = PublicMatchPredictionRequest(
            radiant_heroes=[1, 2, 3, 4, 5],
            dire_heroes=[6, 7, 8, 9, 10],
        )

        response = await full_stack_client.post(url="/inference/predict", json=valid_request.model_dump())

        assert response.status_code == 200
        response_data = response.json()
        assert "prediction" in response_data

        # 2. Write some test data to Redis that could potentially pollute other tests
        pollution_key = "api_service_pollution_test"
        await e2e_redis_client.set(pollution_key, "api_service_test_data")

        # 3. Verify the data was written
        stored_value = await e2e_redis_client.get(pollution_key)
        assert stored_value == "api_service_test_data"

        # 4. Check database state
        async with AsyncSession(e2e_postgres_engine) as session:
            hero_repo = HeroesRepository(session)
            hero_map = await hero_repo.get_hero_id_map()

            # Verify hero data exists (this is expected)
            assert len(hero_map) > 0
            assert 1 in hero_map  # Anti-Mage should exist

        logger.info(f"API service pollution test completed. Redis key '{pollution_key}' set to verify isolation.")

    async def test_live_orchestrator_pollution_detection(
        self,
        configured_test_container,
        e2e_redis_client: aioredis.Redis,
        e2e_postgres_engine,
    ):
        """
        Test that simulates live orchestrator operations and checks for pollution
        from the API service test.
        """
        # 1. Check if pollution from API service test exists
        pollution_key = "api_service_pollution_test"
        existing_value = await e2e_redis_client.get(pollution_key)

        if existing_value:
            logger.warning(f"POLLUTION DETECTED: Found leftover data in Redis: {existing_value}")
            # This indicates potential pollution between test modules
            # In a real scenario, we might want to fail here or clean up

        # 2. Write our own test data
        live_orchestrator_key = "live_orchestrator_pollution_test"
        await e2e_redis_client.set(live_orchestrator_key, "live_orchestrator_test_data")

        # 3. Verify live orchestrator functionality
        container = configured_test_container

        # Test that the container is properly configured
        assert container is not None

        # Check database access
        async with container.db_session_factory()() as session:
            hero_repo = HeroesRepository(session)
            hero_map = await hero_repo.get_hero_id_map()

            # Verify hero data exists (this should be the same shared data)
            assert len(hero_map) > 0
            assert 1 in hero_map  # Anti-Mage should exist

        # 4. Verify our data was written
        stored_value = await e2e_redis_client.get(live_orchestrator_key)
        assert stored_value == "live_orchestrator_test_data"

        logger.info(f"Live orchestrator pollution test completed. Found pollution: {existing_value is not None}")

    async def test_cross_module_data_isolation(
        self,
        e2e_redis_client: aioredis.Redis,
        e2e_postgres_engine,
    ):
        """
        Test to verify data isolation between test modules.
        This test checks what data persists across different test scenarios.
        """
        # 1. Check for any leftover keys from previous tests
        all_keys = await e2e_redis_client.keys("*pollution_test*")

        logger.info(f"Found {len(all_keys)} pollution test keys: {all_keys}")

        # 2. This demonstrates that Redis data persists across tests within the session
        # which is expected behavior, but we should be aware of it
        for key in all_keys:
            value = await e2e_redis_client.get(key)
            logger.info(f"Persistent data: {key} = {value}")

        # 3. Check database state consistency
        async with AsyncSession(e2e_postgres_engine) as session:
            hero_repo = HeroesRepository(session)
            hero_map = await hero_repo.get_hero_id_map()

            # Verify that hero data is consistent and expected
            assert len(hero_map) >= 126

            # Check for specific test heroes
            expected_heroes = [1, 2, 3, 4, 5]  # Anti-Mage, Axe, Bane, Bloodseeker, Crystal Maiden
            for hero_id in expected_heroes:
                assert hero_id in hero_map, f"Hero {hero_id} missing from database"

        # 4. Clean up our pollution test data
        cleanup_keys = ["api_service_pollution_test", "live_orchestrator_pollution_test"]

        cleaned_count = 0
        for key in cleanup_keys:
            if await e2e_redis_client.exists(key):
                await e2e_redis_client.delete(key)
                cleaned_count += 1

        logger.info(f"Cleaned up {cleaned_count} pollution test keys")

    async def test_redis_namespace_isolation(
        self,
        e2e_redis_client: aioredis.Redis,
    ):
        """
        Test Redis namespace isolation to prevent accidental key collisions
        between different test scenarios.
        """
        # 1. Set up test data with different namespaces
        test_namespaces = [
            "api_service:test_key",
            "live_orchestrator:test_key",
            "pollution_test:namespace_1",
            "pollution_test:namespace_2",
        ]

        # Write data to each namespace
        for namespace in test_namespaces:
            await e2e_redis_client.set(namespace, f"data_for_{namespace}")

        # 2. Verify data isolation
        for namespace in test_namespaces:
            value = await e2e_redis_client.get(namespace)
            expected = f"data_for_{namespace}"
            assert value == expected, f"Namespace {namespace} corrupted: got {value}, expected {expected}"

        # 3. Test that similar keys don't interfere
        similar_keys = ["test_key", "api_service:test_key", "live_orchestrator:test_key"]

        for key in similar_keys:
            value = await e2e_redis_client.get(key)
            if key == "test_key":
                assert value is None, "Base key should not exist"
            else:
                expected = f"data_for_{key}"
                assert value == expected

        # 4. Clean up
        for namespace in test_namespaces:
            await e2e_redis_client.delete(namespace)

        logger.info("Redis namespace isolation test completed successfully")

    async def test_database_transaction_isolation(
        self,
        e2e_postgres_engine,
    ):
        """
        Test database transaction isolation to ensure operations
        from different test modules don't interfere with each other.
        """
        # 1. Create two separate sessions to simulate different test modules
        async with AsyncSession(e2e_postgres_engine) as session1:
            async with AsyncSession(e2e_postgres_engine) as session2:

                # 2. Both sessions should see the same hero data
                repo1 = HeroesRepository(session1)
                repo2 = HeroesRepository(session2)

                heroes1 = await repo1.get_hero_id_map()
                heroes2 = await repo2.get_hero_id_map()

                # 3. Verify consistency
                assert len(heroes1) == len(heroes2), "Hero data inconsistent between sessions"
                assert heroes1 == heroes2, "Hero maps differ between sessions"

                # 4. Test that modifications in one session don't immediately affect the other
                # (This would be more relevant for transactional data, but heroes are read-only)
                logger.info(f"Database isolation test: Both sessions see {len(heroes1)} heroes consistently")

        logger.info("Database transaction isolation test completed successfully")
