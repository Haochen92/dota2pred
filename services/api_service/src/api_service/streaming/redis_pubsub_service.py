import redis.asyncio as aioredis
from dota_oracle_common.utils.set_logging import get_logger
from dota_oracle_common.models.api import LiveStateUpdateRequest
import asyncio
import json
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, after_log
import logging

logger = get_logger(__name__)


class RedisPubSubService:
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client

    @retry(
        retry=retry_if_exception_type(aioredis.ConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        after=after_log(logger, logging.WARNING),
        reraise=True,
    )
    async def publish_live_update(self, channel: str, payload: LiveStateUpdateRequest):
        try:
            message = payload.model_dump_json()

            receivers = await self.redis.publish(channel, message)
            logger.info(f"Published update to channel '{channel}'. Received by {receivers} clients.")
            return receivers

        except Exception as e:
            logger.error(f"Failed to publish to Redis channel '{channel}': {e}", exc_info=True)
            raise

    async def listen_to_channel(self, channel: str):
        """An async generator that subscribes to a Redis Channel and yields messages.
        Attempts to reconnect with a new subcriber when server crashed due to connection error

        Args:
            channel (str): channel name in string
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

    async def _get_message_stream(self, channel: str):
        async with self.redis.pubsub() as pubsub:
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to Redis channel: {channel}")

            while True:
                message_dict = await pubsub.get_message(ignore_subscribe_messages=True, timeout=10.0)
                if message_dict:
                    try:
                        yield message_dict["data"]
                    except json.JSONDecodeError:
                        logger.error(f"Error Decoding message: {message_dict['data']}, e")
                        continue
