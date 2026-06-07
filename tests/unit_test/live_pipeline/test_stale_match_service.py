import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from tenacity import RetryError

from dota_oracle_common.models.redis.schema import ConsumedEvent, CompletionPayload
from dota_oracle_common.models.utils.schema import TaskResult
from live_orchestrator_app.services.stale_match_service import StaleMatchService
from live_orchestrator_app.constants.redis_constants import STREAM_PENDING_COMPLETION, COMPLETION_GROUP


# Use pytest-asyncio for async tests
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_redis_service() -> AsyncMock:
    """Provides a mock RedisService with async methods."""
    return AsyncMock()


@pytest.fixture
def mock_task_runner() -> MagicMock:
    """Provides a mock TaskRunner."""
    # We patch the static method run_concurrently
    with patch("dota_oracle_common.utils.async_utils.TaskRunner.run_concurrently", new_callable=AsyncMock) as mock_run:
        yield mock_run


@pytest.fixture
def consumed_event_factory():
    """A simple factory to create ConsumedEvent instances for tests."""

    def _factory(match_id: int, event_id: str) -> ConsumedEvent[CompletionPayload]:
        return ConsumedEvent[CompletionPayload](
            match_id=match_id, event_id=event_id, payload=CompletionPayload(match_id=match_id, radiant_win=True)
        )

    return _factory


class TestStaleMatchService:

    async def test_run_cycle_no_expired_events(self, mock_redis_service: AsyncMock):
        """
        Tests that the cycle exits early and correctly if no expired events are found.
        """
        # ARRANGE
        mock_redis_service.fetch_expired_events.return_value = []
        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT
        result = await service.run_stream_cleaning_cycle()

        # ASSERT
        mock_redis_service.fetch_expired_events.assert_awaited_once()
        mock_redis_service.claim_expired_events.assert_not_awaited()
        assert result == []

    async def test_run_cycle_no_claimed_events(self, mock_redis_service: AsyncMock):
        """
        Tests that the cycle exits correctly if expired IDs are found but none can be claimed.
        """
        # ARRANGE
        mock_redis_service.fetch_expired_events.return_value = ["123-0", "456-0"]
        mock_redis_service.claim_expired_events.return_value = []
        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT
        result = await service.run_stream_cleaning_cycle()

        # ASSERT
        mock_redis_service.fetch_expired_events.assert_awaited_once()
        mock_redis_service.claim_expired_events.assert_awaited_once_with(
            stream_name=service.stream,
            consumer_group=service.group,
            payload_model=CompletionPayload,
            consumer_name="stale_match_consumer",
            events_id_list=["123-0", "456-0"],
        )
        assert result == []

    async def test_run_cycle_full_success_path(
        self,
        mock_redis_service: AsyncMock,
        mock_task_runner: AsyncMock,
        consumed_event_factory,
    ):
        """
        Tests the ideal "happy path" where events are found, claimed, and processed successfully.
        """
        # ARRANGE
        # 1. Mock the return values from RedisService
        expired_ids = ["111-0", "222-0"]
        mock_redis_service.fetch_expired_events.return_value = expired_ids

        claimed_event_1 = consumed_event_factory(match_id=111, event_id="111-0")
        claimed_event_2 = consumed_event_factory(match_id=222, event_id="222-0")
        mock_redis_service.claim_expired_events.return_value = [claimed_event_1, claimed_event_2]

        # 2. Mock the return values from TaskRunner
        # Simulate successful fetch_match_details returning radiant_win=True for both
        task_result_1 = TaskResult(key="111-0", inputs=claimed_event_1, outcome=True)
        task_result_2 = TaskResult(key="222-0", inputs=claimed_event_2, outcome=False)
        mock_task_runner.return_value = [task_result_1, task_result_2]

        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT
        final_results = await service.run_stream_cleaning_cycle()

        # ASSERT
        # 1. Check RedisService calls
        mock_redis_service.fetch_expired_events.assert_awaited_once()
        mock_redis_service.claim_expired_events.assert_awaited_once_with(
            events_id_list=expired_ids,
            stream_name=service.stream,
            consumer_group=service.group,
            consumer_name="stale_match_consumer",
            payload_model=CompletionPayload,
        )

        # 2. Check TaskRunner call
        assert mock_task_runner.call_count == 1

        # 3. Check final output
        assert len(final_results) == 2
        assert final_results[0].match_id == 111
        assert final_results[0].payload.match_outcome is True
        assert final_results[1].match_id == 222
        assert final_results[1].payload.match_outcome is False

        # 4. Ensure DLQ was NOT called
        mock_redis_service.handle_processing_failure.assert_not_awaited()

    async def test_run_cycle_with_processing_failures(
        self,
        mock_redis_service: AsyncMock,
        mock_task_runner: AsyncMock,
        consumed_event_factory,
    ):
        """
        Tests the path where one event succeeds and one fails processing,
        triggering a call to the DLQ.
        """
        # ARRANGE
        expired_ids = ["111-0", "999-0"]  # 999 will be the failing one
        mock_redis_service.fetch_expired_events.return_value = expired_ids

        claimed_event_1 = consumed_event_factory(match_id=111, event_id="111-0")
        claimed_event_fail = consumed_event_factory(match_id=999, event_id="999-0")
        mock_redis_service.claim_expired_events.return_value = [claimed_event_1, claimed_event_fail]

        # Simulate one success and one failure (e.g., ValueError from API)
        task_result_1 = TaskResult(key="111-0", inputs=claimed_event_1, outcome=True)
        failure_exception = ValueError("match_outcome is unavailable for match 999")
        task_result_fail = TaskResult(key="999-0", inputs=claimed_event_fail, outcome=failure_exception)
        mock_task_runner.return_value = [task_result_1, task_result_fail]

        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT
        final_results = await service.run_stream_cleaning_cycle()

        # ASSERT
        # 1. Check final output
        assert len(final_results) == 1, "Only the successful event should be returned"
        assert final_results[0].match_id == 111

        # 2. Assert that the DLQ handler was called for the failed event
        mock_redis_service.handle_processing_failure.assert_awaited_once()
        # Check the arguments of the call
        dlq_call_args = mock_redis_service.handle_processing_failure.call_args.kwargs
        assert dlq_call_args["event_data"] == claimed_event_fail
        assert dlq_call_args["event_id"] == "999-0"
        assert dlq_call_args["error"] == failure_exception

    @patch("live_orchestrator_app.services.stale_match_service.fetch_match_details", new_callable=AsyncMock)
    async def test_fetch_single_match_retry_logic(
        self,
        mock_fetch_details: AsyncMock,
        mock_redis_service: AsyncMock,  # Unused but needed for fixture setup
    ):
        """
        Tests the @retry decorator on _fetch_single_completed_match.
        """
        # ARRANGE
        # Simulate a transient network error followed by a success
        mock_fetch_details.side_effect = [
            asyncio.TimeoutError("API timed out"),
            asyncio.TimeoutError("API timed out again"),
            MagicMock(radiant_win=True),  # Success on the 3rd attempt
        ]

        service = StaleMatchService(redis_service=mock_redis_service)
        fake_event = ConsumedEvent[CompletionPayload](
            match_id=777, event_id="777-0", payload=CompletionPayload(match_id=777, radiant_win=False)
        )

        # ACT
        # This will internally retry due to the tenacity decorator
        result = await service._fetch_single_completed_match(fake_event)

        # ASSERT
        # 1. Check that the fetch function was called 3 times
        assert mock_fetch_details.call_count == 3

        # 2. Check that the final result is the successful one
        assert result is True

    async def test_run_cycle_fetch_expired_events_error(self, mock_redis_service: AsyncMock):
        """
        Tests error handling when fetch_expired_events fails.
        """
        # ARRANGE
        mock_redis_service.fetch_expired_events.side_effect = Exception("Redis connection error")
        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT & ASSERT
        with pytest.raises(Exception, match="Redis connection error"):
            await service.run_stream_cleaning_cycle()

        mock_redis_service.fetch_expired_events.assert_awaited_once()
        mock_redis_service.claim_expired_events.assert_not_awaited()

    async def test_run_cycle_claim_expired_events_error(self, mock_redis_service: AsyncMock):
        """
        Tests error handling when claim_expired_events fails.
        """
        # ARRANGE
        mock_redis_service.fetch_expired_events.return_value = ["123-0"]
        mock_redis_service.claim_expired_events.side_effect = Exception("Failed to claim events")
        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT & ASSERT
        with pytest.raises(Exception, match="Failed to claim events"):
            await service.run_stream_cleaning_cycle()

        mock_redis_service.fetch_expired_events.assert_awaited_once()
        mock_redis_service.claim_expired_events.assert_awaited_once()

    @patch("live_orchestrator_app.services.stale_match_service.fetch_match_details", new_callable=AsyncMock)
    async def test_fetch_single_match_retry_exhaustion(
        self,
        mock_fetch_details: AsyncMock,
        mock_redis_service: AsyncMock,
    ):
        """
        Tests the @retry decorator when all retry attempts are exhausted.
        """
        # ARRANGE
        # Simulate persistent transient failures that exhaust all retry attempts
        mock_fetch_details.side_effect = asyncio.TimeoutError("API always times out")

        service = StaleMatchService(redis_service=mock_redis_service)
        fake_event = ConsumedEvent[CompletionPayload](
            match_id=888, event_id="888-0", payload=CompletionPayload(match_id=888, radiant_win=False)
        )

        # ACT & ASSERT
        with pytest.raises(RetryError):
            await service._fetch_single_completed_match(fake_event)

        # Should have tried 3 times (stop_after_attempt(3))
        assert mock_fetch_details.call_count == 3

    @patch("live_orchestrator_app.services.stale_match_service.fetch_match_details", new_callable=AsyncMock)
    async def test_fetch_single_match_no_match_details(
        self,
        mock_fetch_details: AsyncMock,
        mock_redis_service: AsyncMock,
    ):
        """
        A 404 (fetch_match_details returns None) means "not ingested yet", not a failure:
        it must return None (leave pending) WITHOUT retrying -- retrying a 404 was the
        latency bomb that risked the live cycle timeout.
        """
        # ARRANGE
        mock_fetch_details.return_value = None

        service = StaleMatchService(redis_service=mock_redis_service)
        fake_event = ConsumedEvent[CompletionPayload](
            match_id=999, event_id="999-0", payload=CompletionPayload(match_id=999, radiant_win=False)
        )

        # ACT
        result = await service._fetch_single_completed_match(fake_event)

        # ASSERT — returned None, not raised, and NOT retried.
        assert result is None
        assert mock_fetch_details.call_count == 1

    async def test_fetch_completed_work_items_direct(
        self,
        mock_redis_service: AsyncMock,
        mock_task_runner: AsyncMock,
        consumed_event_factory,
    ):
        """
        Tests the _fetch_completed_work_items method directly.
        """
        # ARRANGE
        claimed_event_1 = consumed_event_factory(match_id=100, event_id="100-0")
        claimed_event_2 = consumed_event_factory(match_id=200, event_id="200-0")
        claimed_events = [claimed_event_1, claimed_event_2]

        # Mock successful processing for both events
        task_result_1 = TaskResult(key="100-0", inputs=claimed_event_1, outcome=True)
        task_result_2 = TaskResult(key="200-0", inputs=claimed_event_2, outcome=False)
        mock_task_runner.return_value = [task_result_1, task_result_2]

        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT
        result = await service._fetch_completed_work_items(claimed_events)

        # ASSERT
        assert len(result) == 2
        assert result[0].match_id == 100
        assert result[0].payload.match_outcome is True
        assert result[1].match_id == 200
        assert result[1].payload.match_outcome is False

        # Verify TaskRunner was called with correct parameters
        mock_task_runner.assert_awaited_once()
        call_args = mock_task_runner.call_args[0]
        concurrent_tasks = call_args[0]
        assert len(concurrent_tasks) == 2
        assert concurrent_tasks[0].key == "100-0"
        assert concurrent_tasks[1].key == "200-0"

    async def test_fetch_completed_work_items_mixed_success_failure(
        self,
        mock_redis_service: AsyncMock,
        mock_task_runner: AsyncMock,
        consumed_event_factory,
    ):
        """
        Tests _fetch_completed_work_items with mixed success/failure results.
        """
        # ARRANGE
        claimed_event_success = consumed_event_factory(match_id=300, event_id="300-0")
        claimed_event_fail = consumed_event_factory(match_id=400, event_id="400-0")
        claimed_events = [claimed_event_success, claimed_event_fail]

        # Mock one success and one failure
        task_result_success = TaskResult(key="300-0", inputs=claimed_event_success, outcome=True)
        failure_exception = ValueError("API error for match 400")
        task_result_fail = TaskResult(key="400-0", inputs=claimed_event_fail, outcome=failure_exception)
        mock_task_runner.return_value = [task_result_success, task_result_fail]

        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT
        result = await service._fetch_completed_work_items(claimed_events)

        # ASSERT
        assert len(result) == 1  # Only the successful one
        assert result[0].match_id == 300
        assert result[0].payload.match_outcome is True

        # Verify DLQ handler was called for the failed event
        mock_redis_service.handle_processing_failure.assert_awaited_once_with(
            event_data=claimed_event_fail,
            event_id="400-0",
            error=failure_exception,
            consumer_group=service.group,
            event_stream=service.stream,
        )

    async def test_constructor_default_values(self):
        """
        Tests that the StaleMatchService constructor sets correct default values.
        """
        # ARRANGE
        mock_redis = AsyncMock()

        # ACT
        service = StaleMatchService(redis_service=mock_redis)

        # ASSERT
        assert service.redis == mock_redis
        assert service.expiry_duration == 7200  # Default value
        assert service.batch_size == 50
        assert service.stream == STREAM_PENDING_COMPLETION
        assert service.group == COMPLETION_GROUP

    async def test_sweep_capped_to_batch_size(
        self, mock_redis_service: AsyncMock, mock_task_runner: AsyncMock, consumed_event_factory
    ):
        """A large backlog must be capped to batch_size per cycle so it can't dominate the live cycle."""
        # ARRANGE
        service = StaleMatchService(redis_service=mock_redis_service)
        too_many = [f"{i}-0" for i in range(1, service.batch_size + 11)]  # batch_size + 10
        mock_redis_service.fetch_expired_events.return_value = too_many
        mock_redis_service.claim_expired_events.return_value = []
        mock_task_runner.return_value = []

        # ACT
        await service.run_stream_cleaning_cycle()

        # ASSERT — only the first batch_size ids were claimed this cycle.
        claimed = mock_redis_service.claim_expired_events.call_args.kwargs["events_id_list"]
        assert len(claimed) == service.batch_size
        assert claimed == too_many[: service.batch_size]

    async def test_404_is_discarded(
        self, mock_redis_service: AsyncMock, mock_task_runner: AsyncMock, consumed_event_factory
    ):
        """A 404 at the stale sweep is the single billed lookup at the end of the wait window,
        so it is terminally discarded -- never re-billed on a later cycle.

        Discard (XACK+XDEL) instead of the retryable DLQ -- otherwise the DLQ sweep would
        re-inject the same unresolvable match and it would churn (and re-charge) forever. If the
        outcome is ever real it still arrives via the proMatches -> DB batch backfill.
        """
        # ARRANGE — by the time it reaches the stale sweep the match is past expiry_duration.
        event = consumed_event_factory(match_id=557, event_id="557-0")
        mock_redis_service.fetch_expired_events.return_value = ["557-0"]
        mock_redis_service.claim_expired_events.return_value = [event]
        mock_task_runner.return_value = [TaskResult(key="557-0", inputs=event, outcome=None)]
        service = StaleMatchService(redis_service=mock_redis_service)

        # ACT
        result = await service.run_stream_cleaning_cycle()

        # ASSERT — not returned as completed, terminally discarded (never re-injected, never DLQ'd).
        assert result == []
        mock_redis_service.handle_processing_failure.assert_not_awaited()
        mock_redis_service.discard_unresolvable_event.assert_awaited_once()
        assert mock_redis_service.discard_unresolvable_event.call_args.kwargs["event_id"] == "557-0"
