import redis.asyncio as aioredis
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.api import LiveStateUpdateRequest
from typing import AsyncGenerator
import asyncio
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, after_log
import logging

logger = get_logger(__name__)


class RedisPubSubService:
    """
    A resilient service for handling Redis Publish/Subscribe operations
    with connection pooling, retry logic, and automatic reconnection.
    """

    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    @retry(
        retry=retry_if_exception_type(aioredis.ConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        after=after_log(logger, logging.WARNING),
        reraise=True,
    )
    async def publish_live_update(self, channel: str, payload: LiveStateUpdateRequest) -> int:
        """
        Publishes a Pydantic model to a Redis channel with robust retry logic.

        This method serializes the payload to JSON and uses Tenacity to
        automatically retry on transient connection errors.

        Args:
            channel: The Redis channel to publish the message to.
            payload: The Pydantic model containing the data to be sent.

        Returns:
            An integer representing the number of subscribers that received the message.

        Raises:
            aioredis.ConnectionError: If publishing fails after all retry attempts.
            Exception: For any other unexpected errors during publishing.
        """
        try:
            message = payload.model_dump_json()

            receivers = await self.redis.publish(channel, message)
            logger.info(f"Published update to channel '{channel}'. Received by {receivers} clients.")
            return receivers

        except Exception as e:
            logger.error(f"Failed to publish to Redis channel '{channel}': {e}", exc_info=True)
            raise

    async def listen_to_channel(self, channel: str) -> AsyncGenerator[str, None]:
        """
        A 'smart' public generator that provides a resilient stream of messages.

        This method owns the reconnection policy. It will continuously attempt
        to listen for messages, handling connection drops by sleeping and
        re-establishing the subscription. It will give up and raise a
        RuntimeError after a set number of consecutive failures.

        Args:
            channel: The Redis channel to subscribe to.
            max_failures: The maximum number of consecutive connection failures
                          before giving up.

        Yields:
            A string containing the message data..
        """
        while True:
            try:
                async for message in self._get_message_stream(channel):
                    yield message
            except aioredis.ConnectionError as e:
                # Gracefully handle redis connection error, by continually retry
                logger.warning(f"Redis connection lost: {e}. Reconnecting in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in Redis subscription for channel '{channel}': {e}", exc_info=True)
                break

    async def _get_message_stream(self, channel: str) -> AsyncGenerator[str, None]:
        """
        A 'dumb' private generator that makes ONE attempt to connect and yield messages.

        It handles non-fatal, message-level errors internally but allows fatal
        ConnectionErrors to propagate up to the caller for handling.

        Args:
            channel: The Redis channel to subscribe to.

        Yields:
            A string containing the raw message data.

        Raises:
            aioredis.ConnectionError: If the connection to Redis is lost during operation.
        """
        async with self.redis.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")

            while True:
                message_dict = await pubsub.get_message(ignore_subscribe_messages=True, timeout=5.0)
                if message_dict:
                    try:
                        yield message_dict["data"]
                    except json.JSONDecodeError:
                        logger.error(f"Error Decoding message: {message_dict['data']}, e")
                        continue
