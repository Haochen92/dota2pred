import redis.asyncio as aioredis
from pydantic import ValidationError
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.api import LiveStateUpdateRequest
from typing import AsyncGenerator
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, after_log
import logging
import asyncio

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

    # Helper methods for pubsub lifecycle
    async def _create_pubsub(self):
        return self.redis.pubsub()

    async def _cleanup_pubsub(self, pubsub, channel: str) -> None:
        logger.info(f"Unsubscribing and closing pubsub for channel: {channel}")
        try:
            await pubsub.unsubscribe(channel)
        except Exception as e:
            logger.warning(f"Ignoring error during pubsub unsubscribe: {e}")
        try:
            # redis.asyncio PubSub.close is awaitable
            await pubsub.close()
        except Exception as e:
            logger.warning(f"Ignoring error during pubsub close: {e}")

    def _validate(self, raw: str) -> LiveStateUpdateRequest | None:
        try:
            return LiveStateUpdateRequest.model_validate_json(raw)
        except ValidationError as ve:
            logger.warning("Dropping invalid message: %s", str(ve)[:200])
            return None

    async def subscribe_to_channel(self, channel: str) -> AsyncGenerator[LiveStateUpdateRequest | None, None]:
        """
        Subscribe to a channel and yield LiveStateUpdateRequest DTOs (or None on heartbeat timeout).
        - Validates each message against the DTO
        - Cleanly unsubscribes/closes on exit
        - Automatically reconnects on Redis connection errors with a small backoff
        - Crucially: stops outer loop if the generator is closed (to avoid leaks)
        """
        backoff = 1.0
        attempt = 0
        while True:
            pubsub = await self._create_pubsub()
            closing = False
            try:
                await pubsub.subscribe(channel)
                logger.info(f"Subscribed to Redis channel: {channel}")
                backoff = 1.0
                attempt = 0
                while True:
                    try:
                        message_dict = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                        if message_dict:
                            dto = self._validate(message_dict["data"])
                            if dto is not None:
                                yield dto
                            # if invalid, skip
                        else:
                            # Idle heartbeat signal
                            yield None
                    except (asyncio.CancelledError, GeneratorExit):
                        # Consumer closed the generator via aclose(); stop cleanly
                        closing = True
                        break
                    except aioredis.ConnectionError as e:
                        attempt += 1
                        logger.warning(
                            "Redis connection lost during listen (attempt %d): %s. Reconnecting in %.1fs...",
                            attempt,
                            e,
                            backoff,
                        )
                        break  # break inner loop to recreate pubsub in outer loop
                    except Exception as e:
                        attempt += 1
                        logger.error(
                            "Unexpected error while listening on channel '%s' (attempt %d): %s",
                            channel,
                            attempt,
                            e,
                            exc_info=True,
                        )
                        break
            finally:
                await self._cleanup_pubsub(pubsub, channel)

            if closing:
                # Do not recreate pubsub; exit generator to prevent connection leaks
                return

            # Backoff before trying to resubscribe to avoid tight loop/log spam
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 5.0)

    async def cache_snapshot(self, key: str, payload: LiveStateUpdateRequest) -> None:
        """
        Caches a Pydantic model snapshot in Redis.

        Args:
            key: The Redis key under which to store the snapshot.
            payload: The Pydantic model containing the data to be cached.

        Raises:
            aioredis.ConnectionError: If there is a connection issue with Redis.
            Exception: For any other unexpected errors during caching.
        """
        try:
            message = payload.model_dump_json()
            await self.redis.set(key, message)
            logger.info(f"Cached snapshot under key '{key}'.")
        except Exception as e:
            logger.error(f"Failed to cache snapshot in Redis under key '{key}': {e}", exc_info=True)
            raise

    async def get_cached_snapshot(self, key: str) -> LiveStateUpdateRequest | None:
        """
        Retrieves a cached snapshot from Redis as a raw JSON string.

        Args:
            key: The Redis key from which to retrieve the snapshot.

        Returns:
            The JSON string if found, otherwise None.
        """
        try:
            message = await self.redis.get(key)
            if message:
                return LiveStateUpdateRequest.model_validate_json(message)
            return None
        except ValidationError as ve:
            logger.warning(f"Cached snapshot under key '{key}' is invalid: {ve}")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve cached snapshot from Redis under key '{key}': {e}", exc_info=True)
            raise
