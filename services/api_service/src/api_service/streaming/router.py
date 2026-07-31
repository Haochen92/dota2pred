from fastapi import Request, Response, status, APIRouter, HTTPException
import asyncio
from dota_oracle_common.models.api import LiveStateUpdateRequest
from dota_oracle_common.utils import get_logger
from starlette.responses import StreamingResponse
from api_service.dependencies import PubSub
from .redis_pubsub_service import RedisPubSubService

from .pubsub_hub import PubSubHub

"""
SSE Endpoint
"""

# Constants
LIVE_MATCH_UPDATES_CHANNEL = "live-match-updates"
LAST_LIVE_SNAPSHOT_KEY = "last-live-snapshot"

# Instantiate supporting services
logger = get_logger(__name__)

# Instantiate APIrouter
router = APIRouter(
    prefix="/streaming",
    tags=["streaming"],
    responses={404: {"description": "Streaming endpoint not available"}},
)


# Route Handlers
@router.post(
    "/live-state-update", summary="Publish messages from streaming backend", status_code=status.HTTP_202_ACCEPTED
)
async def post_live_state_update(request_payload: LiveStateUpdateRequest, pubsub_service: PubSub):
    logger.info(f"Received update for {len(request_payload.live_matches)} matches")

    try:
        await asyncio.sleep(0.01)
        await pubsub_service.publish_live_update(channel=LIVE_MATCH_UPDATES_CHANNEL, payload=request_payload)

        # Cache the latest snapshot for new clients
        await pubsub_service.cache_snapshot(key=LAST_LIVE_SNAPSHOT_KEY, payload=request_payload)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to publish live update: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish live update")


@router.get("/snapshot/live_matches", summary="Latest live-match snapshot (poll fallback)")
async def get_live_snapshot(pubsub_service: PubSub) -> Response:
    snapshot = await pubsub_service.get_cached_snapshot(key=LAST_LIVE_SNAPSHOT_KEY)
    if snapshot is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return Response(
        content=snapshot.model_dump_json(),
        media_type="application/json",
        headers={"Cache-Control": "public, max-age=30"},
    )


async def sse_event_stream(request: Request, hub: PubSubHub, pubsub_service: RedisPubSubService):
    """
    SSE generator using a single-process PubSub hub for fan-out.
    Sends cached snapshot, then drains per-client queue with heartbeat on idle.
    """
    # Send initial comment to open SSE stream
    yield ": connected\n\n"

    # Brief delay to ensure handshake is flushed
    await asyncio.sleep(0.05)

    # Send cached snapshot as a single SSE data event if present
    cached_request = await pubsub_service.get_cached_snapshot(key=LAST_LIVE_SNAPSHOT_KEY)
    if cached_request:
        logger.info("Sending cached snapshot to new SSE client.")
        yield f"data: {cached_request.model_dump_json()}\n\n"

    # Register this client to the hub
    q = hub.register()
    try:
        while True:
            if await request.is_disconnected():
                logger.info("SSE Client disconnected.")
                break
            try:
                dto: LiveStateUpdateRequest = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {dto.model_dump_json()}\n\n"
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    except Exception as e:
        logger.error(f"Error in SSE event stream: {e}")
        raise
    finally:
        hub.unregister(q)


@router.get("/sse/live_matches", summary="Subscriber's Gateway for SSE")
async def get_live_state_sse(request: Request):
    """
    Establishes an SSE connection. The client will receive updates
    pushed from the /live-state-update endpoint via Redis Pub/Sub.
    """
    app = request.app
    hub: PubSubHub = app.state.pubsub_hub
    pubsub_service: RedisPubSubService = app.state.pubsub_service

    return StreamingResponse(
        sse_event_stream(request, hub, pubsub_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
