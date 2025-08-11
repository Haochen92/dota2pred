import pytest
import httpx


# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

f_path = "live_orchestrator_app.services.notifications_service"


class TestNotificationService:

    async def test_notify_state_change_success_with_live_matches(
        self,
        notification_service,
        mock_redis_service,
        mock_match_repository,
        match_prediction_table_factory,
        match_table_factory,
        mocker,
    ):
        """
        GIVEN there are live match IDs in Redis and the DB fetch is successful
        WHEN notify_state_change is called
        THEN it should fetch details, build a payload, and call the API endpoint successfully
        """
        # --- ARRANGE ---
        # 1. Mock Redis to return a set of live match IDs
        live_match_ids = {101, 102}
        mock_redis_service.get_live_match_ids.return_value = live_match_ids

        # 2. Mock the MatchRepository to return mock data
        # Create mock DB objects using your factories
        mock_prediction_1 = match_prediction_table_factory.build(prediction=True)
        mock_prediction_2 = match_prediction_table_factory.build(prediction=True)
        mock_db_matches = [
            match_table_factory.build(match_id=101, predictions=[mock_prediction_1]),
            match_table_factory.build(match_id=102, predictions=[mock_prediction_2]),
        ]

        # Mock the MatchRepository class
        MockRepo = mocker.patch(f"{f_path}.MatchRepository", return_value=mock_match_repository)
        mock_match_repository.get_match_details.return_value = mock_db_matches

        # 3. Mock the internal call_api_endpoint to simulate a successful API call
        mock_call_api = mocker.patch.object(
            notification_service,
            "call_api_endpoint",
            new_callable=mocker.AsyncMock,
            return_value={"successful": True, "status_code": 200, "error": None},
        )

        # --- ACT ---
        result = await notification_service.notify_state_change()

        # --- ASSERT ---
        # Verify dependencies were called correctly
        mock_redis_service.get_live_match_ids.assert_awaited_once()
        MockRepo.assert_called_once()
        mock_match_repository.get_match_details.assert_awaited_once_with(
            input_id_list=list(live_match_ids), relationship_fields=["predictions"]
        )

        # Verify the API was called with the correct payload structure
        mock_call_api.assert_awaited_once()
        sent_payload = mock_call_api.call_args[0][0]  # Get the first positional arg
        assert "live_matches" in sent_payload
        assert len(sent_payload["live_matches"]) == 2
        assert sent_payload["live_matches"][0]["match_id"] == 101
        assert sent_payload["live_matches"][0]["predicted_outcome"] is True  # Check mapper logic

        # Verify the final result is the success status from the API call
        assert result["successful"] is True
        assert result["status_code"] == 200

    async def test_notify_state_change_with_no_live_matches(self, notification_service, mock_redis_service, mocker):
        """
        GIVEN there are no live match IDs in Redis
        WHEN notify_state_change is called
        THEN it should send a payload with an empty list and return the API status
        """
        # --- ARRANGE ---
        mock_redis_service.get_live_match_ids.return_value = set()  # Empty set

        mock_call_api = mocker.patch.object(
            notification_service,
            "call_api_endpoint",
            new_callable=mocker.AsyncMock,
            return_value={"successful": True, "status_code": 200, "error": None},
        )

        # --- ACT ---
        result = await notification_service.notify_state_change()

        # --- ASSERT ---
        mock_redis_service.get_live_match_ids.assert_awaited_once()

        # Verify the API was called with the correct empty payload
        mock_call_api.assert_awaited_once_with({"live_matches": []})
        assert result["successful"] is True

    async def test_notify_state_change_fails_on_db_error(
        self, notification_service, mock_redis_service, mock_match_repository, mocker
    ):
        """
        GIVEN Redis returns live match IDs
        WHEN the database fetch raises an exception
        THEN notify_state_change should re-raise that exception and NOT call the API
        """
        # --- ARRANGE ---
        mock_redis_service.get_live_match_ids.return_value = {101}
        db_error = ValueError("Database connection failed")

        # Mock the MatchRepository class
        mocker.patch(f"{f_path}.MatchRepository", return_value=mock_match_repository)
        mock_match_repository.get_match_details.side_effect = db_error

        # Mock the API call method
        mock_call_api = mocker.patch.object(notification_service, "call_api_endpoint", new_callable=mocker.AsyncMock)

        # --- ACT & ASSERT ---
        # Use pytest.raises to assert that the specific exception is raised
        with pytest.raises(ValueError, match="Database connection failed"):
            await notification_service.notify_state_change()

        # Verify the API was never called
        mock_call_api.assert_not_awaited()

    async def test_call_api_endpoint_retries_on_network_error_and_fails(self, notification_service, mocker):
        """
        GIVEN the httpx client will raise a network error
        WHEN call_api_endpoint is called
        THEN it should retry 3 times and return a failure status
        """
        # --- ARRANGE ---
        network_error = httpx.ConnectError("Connection refused")

        # Mock the http_client's post method directly
        mock_post = mocker.patch.object(
            notification_service.http_client, "post", new_callable=mocker.AsyncMock, side_effect=network_error
        )

        payload = {"live_matches": []}

        # --- ACT ---
        result = await notification_service.call_api_endpoint(payload)

        # --- ASSERT ---
        # Verify tenacity retried the correct number of times
        assert mock_post.await_count == 3  # 1 initial call + 2 retries

        # Verify the final status is failure
        assert result["successful"] is False
        assert result["error"] == "Network request failed after all retry attempts"

    async def test_call_api_endpoint_does_not_retry_on_http_status_error(self, notification_service, mocker):
        """
        GIVEN the httpx client will raise an HTTP status error (e.g., 500)
        WHEN call_api_endpoint is called
        THEN it should NOT retry and immediately return a failure status
        """
        # --- ARRANGE ---
        # Create a proper mock request and response
        mock_request = httpx.Request("POST", "http://api-service:8000/internal/live-state-update")
        mock_response = httpx.Response(status_code=500, request=mock_request)
        mock_response._text = "Internal Server Error"
        http_error = httpx.HTTPStatusError(message="Server error", request=mock_request, response=mock_response)

        # Mock the http_client's post method directly
        mock_post = mocker.patch.object(
            notification_service.http_client, "post", new_callable=mocker.AsyncMock, side_effect=http_error
        )

        payload = {"live_matches": []}

        # --- ACT ---
        result = await notification_service.call_api_endpoint(payload)

        # --- ASSERT ---
        # Verify it was called only ONCE
        assert mock_post.await_count == 1

        # Verify the final status reflects the HTTP error
        assert result["successful"] is False
        assert result["status_code"] == 500
        assert "API service returned an error" in result["error"]
