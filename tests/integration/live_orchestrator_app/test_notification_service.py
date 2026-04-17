import pytest
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from live_orchestrator_app.services.notifications_service import NotificationService
from dota_oracle_common.models.match import MatchNotifcationAPIPayload

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestNotificationServiceIntegration:
    """Integration tests for NotificationService with actual database and mocked Redis."""

    async def test_fetch_match_payloads_with_league_data(
        self,
        db_session: AsyncSession,
        test_session_factory: async_sessionmaker[AsyncSession],
        mock_redis_service,
        match_table_factory,
        match_prediction_table_factory,
        league_table_factory,
        mock_http_client,
    ):
        """
        GIVEN: Matches exist in the database with league_data relationships
        WHEN: _fetch_match_payloads is called
        THEN: It should return MatchNotificationAPIPayload objects with league_data populated
        """
        # Create league data
        test_league = league_table_factory.build(leagueid=1001, name="Test League", tier="professional")

        # Create matches with predictions and link to league
        match1 = match_table_factory.build(
            match_id=100001,
            leagueid=1001,
            predictions=[match_prediction_table_factory.build(prediction=True)],
        )
        match2 = match_table_factory.build(
            match_id=100002,
            leagueid=1001,
            predictions=[match_prediction_table_factory.build(prediction=False)],
        )

        # Set up relationships
        match1.league_data = test_league
        match2.league_data = test_league

        # Insert test data using the same session factory that notification service will use
        async with test_session_factory() as session:
            session.add_all([test_league, match1, match2])
            await session.commit()

        # Create notification service using the real session factory
        notification_service = NotificationService(
            redis_service=mock_redis_service,
            db_session_factory=test_session_factory,
            http_client=mock_http_client,
        )

        # Test the method
        match_ids_set = {100001, 100002}
        payloads = await notification_service._fetch_match_payloads(match_ids_set)

        # Assertions
        assert len(payloads) == 2

        # Check that all payloads are MatchNotificationAPIPayload instances
        for payload in payloads:
            assert isinstance(payload, MatchNotifcationAPIPayload)
            assert hasattr(payload, "league_data")
            assert payload.league_data is not None
            assert payload.league_data.leagueid == 1001
            assert payload.league_data.name == "Test League"
            assert payload.league_data.tier == "professional"

        # Check specific match details
        payload_by_match = {p.match_id: p for p in payloads}

        assert payload_by_match[100001].predicted_outcome is True
        assert payload_by_match[100002].predicted_outcome is False

    async def test_notify_state_change_with_league_data_integration(
        self,
        db_session: AsyncSession,
        test_session_factory: async_sessionmaker[AsyncSession],
        mock_redis_service,
        match_table_factory,
        match_prediction_table_factory,
        league_table_factory,
    ):
        """
        GIVEN: Live matches exist in Redis and database with league data
        WHEN: notify_state_change is called
        THEN: It should fetch complete match data with league_data and send proper payload
        """
        # Create test league
        test_league = league_table_factory.build(leagueid=2001, name="Championship League", tier="premium")

        # Create match with prediction and league relationship
        test_match = match_table_factory.build(
            match_id=200001,
            leagueid=2001,
            predictions=[match_prediction_table_factory.build(prediction=True)],
        )
        test_match.league_data = test_league

        # Insert test data using the same session factory that notification service will use
        async with test_session_factory() as session:
            session.add_all([test_league, test_match])
            await session.commit()

        # Setup mock Redis to return our test match ID
        mock_redis_service.get_live_match_ids.return_value = {200001}

        # Create mock HTTP client to capture the API call
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = AsyncMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        # Create notification service using the real session factory
        notification_service = NotificationService(
            redis_service=mock_redis_service,
            db_session_factory=test_session_factory,
            http_client=mock_http_client,
        )

        # Call the method
        result = await notification_service.notify_state_change()

        # Verify result
        assert result["successful"] is True
        assert result["status_code"] == 200

        # Verify HTTP client was called with correct payload
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args

        # Extract the JSON payload that was sent
        sent_json = call_args[1]["json"]

        # Verify the structure
        assert "live_matches" in sent_json
        assert len(sent_json["live_matches"]) == 1

        match_payload = sent_json["live_matches"][0]
        assert match_payload["match_id"] == 200001
        assert match_payload["predicted_outcome"] is True
        assert "league_data" in match_payload
        assert match_payload["league_data"]["leagueid"] == 2001
        assert match_payload["league_data"]["name"] == "Championship League"
        assert match_payload["league_data"]["tier"] == "premium"

    async def test_notify_state_change_with_missing_league_data(
        self,
        db_session: AsyncSession,
        test_session_factory: async_sessionmaker[AsyncSession],
        mock_redis_service,
        match_table_factory,
        match_prediction_table_factory,
    ):
        """
        GIVEN: A match exists without league_data relationship
        WHEN: notify_state_change is called
        THEN: It should handle the missing league_data gracefully
        """
        # Create match without league relationship
        test_match = match_table_factory.build(
            match_id=300001,
            leagueid=None,  # No league ID
            predictions=[match_prediction_table_factory.build(prediction=False)],
        )

        # Insert test data using the same session factory that notification service will use
        async with test_session_factory() as session:
            session.add(test_match)
            await session.commit()

        # Setup mock Redis
        mock_redis_service.get_live_match_ids.return_value = {300001}

        # Create mock HTTP client
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = AsyncMock()

        mock_http_client = AsyncMock()
        mock_http_client.post.return_value = mock_response

        # Create notification service using the real session factory
        notification_service = NotificationService(
            redis_service=mock_redis_service,
            db_session_factory=test_session_factory,
            http_client=mock_http_client,
        )

        # Call the method
        result = await notification_service.notify_state_change()

        # Verify it still works
        assert result["successful"] is True
        assert result["status_code"] == 200

        # Verify HTTP client was called
        mock_http_client.post.assert_called_once()
        call_args = mock_http_client.post.call_args
        sent_json = call_args[1]["json"]

        assert len(sent_json["live_matches"]) == 1
        match_payload = sent_json["live_matches"][0]
        assert match_payload["match_id"] == 300001
        assert match_payload["predicted_outcome"] is False
        # league_data might be None or not present, which is acceptable

    async def test_fetch_match_payloads_returns_empty_for_nonexistent_matches(
        self,
        db_session: AsyncSession,
        test_session_factory: async_sessionmaker[AsyncSession],
        mock_redis_service,
        mock_http_client,
    ):
        """
        GIVEN: Match IDs that don't exist in the database
        WHEN: _fetch_match_payloads is called
        THEN: It should return an empty list
        """
        # Create notification service using the real session factory
        notification_service = NotificationService(
            redis_service=mock_redis_service,
            db_session_factory=test_session_factory,
            http_client=mock_http_client,
        )

        # Test with non-existent match IDs
        nonexistent_ids = {999999, 888888}
        payloads = await notification_service._fetch_match_payloads(nonexistent_ids)

        # Should return empty list
        assert payloads == []
