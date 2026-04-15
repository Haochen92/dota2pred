import pytest
from unittest.mock import AsyncMock

import redis.asyncio as aioredis

from api_service.streaming.redis_pubsub_service import RedisPubSubService
from ...factories.api_service_factory import LiveStateUpdateRequestFactory


class TestRedisPubSubService:
    async def test_publish_calls_redis_correctly(self, unit_test_redis_pubsub_service: RedisPubSubService):
        unit_test_redis_pubsub_service.redis.publish.return_value = 1
        mock_publish = unit_test_redis_pubsub_service.redis.publish

        test_channel = "live-updates"
        mock_payload = LiveStateUpdateRequestFactory.build()
        expected_json = mock_payload.model_dump_json()

        receivers = await unit_test_redis_pubsub_service.publish_live_update(channel=test_channel, payload=mock_payload)

        mock_publish.assert_awaited_once_with(test_channel, expected_json)
        assert receivers == 1

    async def test_publish_retries_and_raises_exception(self, unit_test_redis_pubsub_service: RedisPubSubService):
        unit_test_redis_pubsub_service.redis.publish.side_effect = aioredis.ConnectionError("Simulated Failure")
        mock_publish = unit_test_redis_pubsub_service.redis.publish

        mock_payload = LiveStateUpdateRequestFactory.build()

        with pytest.raises(aioredis.ConnectionError):
            await unit_test_redis_pubsub_service.publish_live_update(channel="any-channel", payload=mock_payload)

        assert mock_publish.await_count == 3

    async def test_subscribe_to_channel_yields_valid_messages_successfully(
        self,
        mocker,
        unit_test_redis_pubsub_service: RedisPubSubService,
    ):
        payload = LiveStateUpdateRequestFactory.build()
        mock_pubsub = AsyncMock()
        mock_pubsub.get_message = AsyncMock(return_value={"data": payload.model_dump_json()})

        mock_create_pubsub = mocker.patch.object(
            unit_test_redis_pubsub_service,
            "_create_pubsub",
            new_callable=AsyncMock,
            return_value=mock_pubsub,
        )

        generator = unit_test_redis_pubsub_service.subscribe_to_channel("test-channel")
        received_message = await anext(generator)
        await generator.aclose()

        mock_create_pubsub.assert_awaited_once()
        mock_pubsub.subscribe.assert_awaited_once_with("test-channel")
        mock_pubsub.unsubscribe.assert_awaited_once_with("test-channel")
        mock_pubsub.close.assert_awaited_once()
        assert received_message == payload
