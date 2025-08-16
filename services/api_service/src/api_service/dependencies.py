from typing import Annotated
from fastapi import Request, Depends
from .streaming.redis_pubsub_service import RedisPubSubService


# Dependency Provider
def get_pubsub_service(request: Request) -> RedisPubSubService:
    return request.app.state.pubsub_service


PubSub = Annotated[RedisPubSubService, Depends(get_pubsub_service)]
