from fastapi import Request, status, APIRouter, HTTPException
import asyncio
from dota_oracle_common.models.api import LiveStateUpdateRequest
from dota_oracle_common.utils import get_logger
from starlette.responses import StreamingResponse
from api_service.dependencies import PubSub
from .redis_pubsub_service import RedisPubSubService

"""
SSE Endpoint
"""

# Constants
LIVE_MATCH_UPDATES_CHANNEL = "live-match-updates"

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
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Failed to publish live update: {e}")
        raise HTTPException(status_code=500, detail="Failed to publish live update")


async def sse_event_stream(request: Request, pubsub_service: RedisPubSubService):
    """
    Generator function that yields SSE events.
    Core logic fof SSE Stream
    """

    try:
        # Send initial handshake
        yield ": connected\n"

        # Brief delay to ensure handshake is flushed before starting Redis listener
        await asyncio.sleep(0.05)

        # Listen for Redis messages
        async for message_json in pubsub_service.listen_to_channel(LIVE_MATCH_UPDATES_CHANNEL):
            if await request.is_disconnected():
                logger.info("SSE Client disconnected.")
                break

            if message_json:
                yield f"data: {message_json}\n\n"

    except Exception as e:
        logger.error(f"Error in SSE event stream: {e}")
        raise


@router.get("/sse/live_matches", summary="Subscriber's Gateway for SSE")
async def get_live_state_sse(request: Request, pubsub_service: PubSub):
    """
    Establishes an SSE connection. The client will receive updates
    pushed from the /live-state-update endpoint via Redis Pub/Sub.
    """
    return StreamingResponse(sse_event_stream(request, pubsub_service), media_type="text/event-stream")
