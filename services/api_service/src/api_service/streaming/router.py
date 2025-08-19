from fastapi import Request, status, APIRouter
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
    "/live-state-update", summary="Received live match updates from the backend", status_code=status.HTTP_202_ACCEPTED
)
async def post_live_state_update(request_payload: LiveStateUpdateRequest, pubsub_service: PubSub):
    logger.info(f"Received update for {len(request_payload.live_matches)} matches")

    await pubsub_service.publish_live_update(channel=LIVE_MATCH_UPDATES_CHANNEL, payload=request_payload)

    return {"status": "success"}


async def sse_event_stream(request: Request, pubsub_service: RedisPubSubService):
    """
    Generator function that yields SSE events.
    """
    async for message_json in pubsub_service.listen_to_channel(LIVE_MATCH_UPDATES_CHANNEL):
        if await request.is_disconnected():
            logger.info("SSE Client disconnected.")
            break

        if message_json:
            event_delimiter = "\n\n"
            yield f"data: {message_json}{event_delimiter}"


@router.get("/sse/live_matches", summary="SSE endpoint for frontend clients to get live match updates")
async def get_live_state_sse(request: Request, pubsub_service: PubSub):
    """
    Establishes an SSE connection. The client will receive updates
    pushed from the /live-state-update endpoint via Redis Pub/Sub.
    """
    return StreamingResponse(sse_event_stream(request, pubsub_service), media_type="text/event-stream")
