import pytest
import httpx

# Mark all tests in this file as async
pytestmark = pytest.mark.asyncio

F_PATH = "live_orchestrator_app.services.notifications_service"


class TestNotificationService:
    """Tests for the NotificationService, aligned with modern exception handling."""

    # --- Tests for the main public method: notify_state_change ---

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
        THEN it should fetch details, call the API, and return a success dictionary
        """
        # --- ARRANGE ---
        live_match_ids = {101, 102}
        mock_redis_service.get_live_match_ids.return_value = live_match_ids

        mock_db_matches = [
            match_table_factory.build(
                match_id=101, predictions=[match_prediction_table_factory.build(prediction=True)]
            ),
            match_table_factory.build(
                match_id=102, predictions=[match_prediction_table_factory.build(prediction=False)]
            ),
        ]
        MockRepo = mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)
        mock_match_repository.get_match_details.return_value = mock_db_matches

        mock_call_api = mocker.patch.object(
            notification_service,
            "call_api_endpoint",
            autospec=True,
            return_value={"status_code": 200},
        )

        # --- ACT ---
        result = await notification_service.notify_state_change()

        # --- ASSERT ---
        mock_redis_service.get_live_match_ids.assert_awaited_once()
        MockRepo.assert_called_once()
        mock_match_repository.get_match_details.assert_awaited_once_with(
            input_id_list=list(live_match_ids), relationship_fields=["predictions"]
        )

        # Verify the API was called with a correctly mapped payload
        mock_call_api.assert_awaited_once()
        sent_payload = mock_call_api.call_args[0][0]
        assert len(sent_payload["live_matches"]) == 2
        assert sent_payload["live_matches"][0]["match_id"] == 101
        assert sent_payload["live_matches"][0]["predicted_outcome"] is True

        # REVISION: The final result is constructed by notify_state_change itself.
        assert result == {"successful": True, "status_code": 200}

    async def test_notify_state_change_with_no_live_matches(self, notification_service, mock_redis_service, mocker):
        """
        GIVEN there are no live match IDs in Redis
        WHEN notify_state_change is called
        THEN it should send an empty payload and return a success dictionary
        """
        # --- ARRANGE ---
        mock_redis_service.get_live_match_ids.return_value = set()
        mock_call_api = mocker.patch.object(
            notification_service,
            "call_api_endpoint",
            autospec=True,
            return_value={"status_code": 200},
        )

        # --- ACT ---
        result = await notification_service.notify_state_change()

        # --- ASSERT ---
        mock_redis_service.get_live_match_ids.assert_awaited_once()
        mock_call_api.assert_awaited_once_with({"live_matches": []})
        assert result == {"successful": True, "status_code": 200}

    async def test_notify_state_change_handles_api_failure(self, notification_service, mock_redis_service, mocker):
        """
        GIVEN a call to the API endpoint will ultimately fail (e.g., after all retries)
        WHEN notify_state_change is called
        THEN it should CATCH the exception and return a failure dictionary
        """
        # --- ARRANGE ---
        mock_redis_service.get_live_match_ids.return_value = set()
        api_error = httpx.RequestError("Could not connect to endpoint")

        mock_call_api = mocker.patch.object(
            notification_service,
            "call_api_endpoint",
            autospec=True,
            side_effect=api_error,
        )

        # --- ACT ---
        result = await notification_service.notify_state_change()

        # --- ASSERT ---
        mock_call_api.assert_awaited_once()
        assert result["successful"] is False
        assert str(api_error) in result["error"]

    async def test_notify_state_change_returns_failure_on_db_error(
        self, notification_service, mock_redis_service, mock_match_repository, mocker
    ):
        """
        GIVEN Redis returns IDs but the database fetch fails
        WHEN notify_state_change is called
        THEN it should CATCH the DB exception, NOT call the API, and return a failure dictionary
        """
        # --- ARRANGE ---
        mock_redis_service.get_live_match_ids.return_value = {101}
        db_error = ValueError("Database connection failed")

        mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)
        mock_match_repository.get_match_details.side_effect = db_error

        mock_call_api = mocker.patch.object(notification_service, "call_api_endpoint", autospec=True)

        # --- ACT ---
        result = await notification_service.notify_state_change()

        # --- ASSERT ---
        assert result["successful"] is False
        assert "An unexpected error occurred" in result["error"]
        assert "Database connection failed" in result["error"]

        mock_call_api.assert_not_awaited()

    # --- Tests for the internal method: call_api_endpoint ---
    # These tests ensure the retry logic and exception raising works as expected.

    async def test_call_api_endpoint_retries_and_then_raises(self, notification_service):
        """
        GIVEN the HTTP client will consistently raise a retryable network error
        WHEN call_api_endpoint is called
        THEN it should retry 3 times and then RAISE the final exception
        """
        # --- ARRANGE ---
        network_error = httpx.ConnectError("Connection refused")
        # To test tenacity, we mock the object it's calling: the http_client's post method.
        # mock_post = AsyncMock(side_effect=network_error)
        # notification_service.http_client.post = mock_post
        mock_post = notification_service.http_client.post
        mock_post.side_effect = network_error

        # --- ACT & ASSERT ---
        # REVISION: Assert that the function RAISES the exception after exhausting retries.
        with pytest.raises(httpx.ConnectError, match="Connection refused"):
            await notification_service.call_api_endpoint(payload={"live_matches": []})

        # Verify tenacity retried the correct number of times (1 initial call + 2 retries)
        assert mock_post.await_count == 3

    async def test_call_api_endpoint_fails_immediately_on_non_retryable_error(self, notification_service):
        """
        GIVEN the HTTP client will raise a non-retryable error (e.g., 400 Bad Request)
        WHEN call_api_endpoint is called
        THEN it should attempt the call only ONCE and immediately RAISE the exception
        """
        # --- ARRANGE ---
        mock_request = httpx.Request("POST", "http://test.url")
        # Use a 4xx error code, which is_retryable_error should return False for.
        mock_response = httpx.Response(status_code=400, request=mock_request, text="Bad Request")
        http_error = httpx.HTTPStatusError(message="Bad Request", request=mock_request, response=mock_response)

        mock_post = notification_service.http_client.post
        mock_post.side_effect = http_error

        # --- ACT & ASSERT ---
        # REVISION: Assert that the function RAISES the exception immediately.
        with pytest.raises(httpx.HTTPStatusError, match="Bad Request"):
            await notification_service.call_api_endpoint(payload={"live_matches": []})

        # Verify it was called only ONCE
        assert mock_post.await_count == 1
