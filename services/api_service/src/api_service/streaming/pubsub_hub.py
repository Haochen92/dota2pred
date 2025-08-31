import asyncio
from typing import Set
from dota_oracle_common.models.api import LiveStateUpdateRequest
from .redis_pubsub_service import RedisPubSubService
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)


class PubSubHub:
    """
    Single Redis Pub/Sub subscriber per process with fan-out to SSE clients.
    - start(): begins one background task that listens on Redis and broadcasts DTOs
    - register(): returns an asyncio.Queue to receive DTOs; caller must unregister()
    - stop(): stops the background task
    """

    def __init__(self, redis_service: RedisPubSubService, channel: str, max_queue_size: int = 100):
        self._redis_service = redis_service
        self._channel = channel
        self._queues: Set[asyncio.Queue[LiveStateUpdateRequest]] = set()
        self._task: asyncio.Task | None = None
        self._max_queue_size = max_queue_size
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._task = asyncio.create_task(self._run(), name=f"PubSubHub[{self._channel}]")
        logger.info("PubSubHub started for channel '%s'", self._channel)

    async def stop(self) -> None:
        if not self._started:
            return
        self._started = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            finally:
                self._task = None
        # Optionally drain/clear queues; callers will drop references on disconnect.
        logger.info("PubSubHub stopped for channel '%s'", self._channel)

    def register(self) -> asyncio.Queue[LiveStateUpdateRequest]:
        q: asyncio.Queue[LiveStateUpdateRequest] = asyncio.Queue(maxsize=self._max_queue_size)
        self._queues.add(q)
        logger.debug("Registered SSE queue (total=%d)", len(self._queues))
        return q

    def unregister(self, q: asyncio.Queue[LiveStateUpdateRequest]) -> None:
        self._queues.discard(q)
        logger.debug("Unregistered SSE queue (total=%d)", len(self._queues))

    async def _broadcast(self, dto: LiveStateUpdateRequest) -> None:
        # Snapshot of listeners to avoid mutation during iteration
        for q in list(self._queues):
            if q.full():
                # Drop oldest to keep recent updates flowing
                try:
                    _ = q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(dto)
            except asyncio.QueueFull:
                # If still full, drop and continue
                logger.debug("Dropping update for a slow consumer queue")
                continue

    async def _run(self) -> None:
        try:
            listener = self._redis_service.subscribe_to_channel(self._channel)
            async for dto_or_none in listener:
                if dto_or_none is None:
                    # Hub does not broadcast heartbeats; clients send their own on timeout
                    continue
                await self._broadcast(dto_or_none)
        except asyncio.CancelledError:
            logger.info("PubSubHub task cancelled")
            raise
        except Exception as e:
            logger.error("PubSubHub encountered an error: %s", e, exc_info=True)
        finally:
            # Nothing to cleanup here; Redis service handles its own cleanup
            logger.info("PubSubHub loop exited for channel '%s'", self._channel)
