import pytest
from api_service.streaming.redis_pubsub_service import RedisPubSubService
from ...factories.api_service_factory import LiveStateUpdateRequestFactory
import redis.asyncio as aioredis

f_path = "api_service.streaming.redis_pubsub_service.RedisPubSubService"


class TestRedisPubSubService:

    async def test_publish_calls_redis_correctly(self, unit_test_redis_pubsub_service: RedisPubSubService):
        # ARRANGE

        # Configure the mock's return value
        unit_test_redis_pubsub_service.redis.publish.return_value = 1
        mock_publish = unit_test_redis_pubsub_service.redis.publish

        test_channel = "live-updates"
        mock_payload = LiveStateUpdateRequestFactory.build()
        expected_json = mock_payload.model_dump_json()

        # ACT
        receivers = await unit_test_redis_pubsub_service.publish_live_update(channel=test_channel, payload=mock_payload)

        # ASSERT
        mock_publish.assert_awaited_once_with(test_channel, expected_json)
        assert receivers == 1

    # --- TEST 2: The Failure Case with Tenacity ---
    async def test_publish_retries_and_raises_exception(self, unit_test_redis_pubsub_service: RedisPubSubService):
        # ARRANGE
        unit_test_redis_pubsub_service.redis.publish.side_effect = aioredis.ConnectionError("Simulated Failure")
        mock_publish = unit_test_redis_pubsub_service.redis.publish

        mock_payload = LiveStateUpdateRequestFactory.build()

        # ACT & ASSERT
        with pytest.raises(aioredis.ConnectionError):
            await unit_test_redis_pubsub_service.publish_live_update(channel="any-channel", payload=mock_payload)

        # ASSERT the call count to verify tenacity's retries
        assert mock_publish.await_count == 3

    async def test_listen_to_channel_yield_messages_successfully(
        self, mocker, unit_test_redis_pubsub_service: RedisPubSubService
    ):

        mock_messages = ['{"message":"one"}', '{"message":"two"}']

        # Arrange
        async def mock_stream(self, channel: str):
            for message in mock_messages:
                yield message

        mock_get_stream = mocker.patch(f"{f_path}._get_message_stream", side_effect=mock_stream, autospec=True)

        # Act

        received_messages = []

        async for message in unit_test_redis_pubsub_service.listen_to_channel("test-channel"):
            received_messages.append(message)
            if len(received_messages) == len(mock_messages):
                break

        mock_get_stream.assert_called_once_with(unit_test_redis_pubsub_service, "test-channel")

        assert len(received_messages) == len(mock_messages)
        assert received_messages[0] == mock_messages[0]
        assert received_messages[1] == mock_messages[1]
