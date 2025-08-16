import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dota_oracle_common.utils import get_logger
from dota_oracle_common.redis_component.redis_client_factory import RedisClientFactory
from contextlib import asynccontextmanager

# import from routes
from .streaming.redis_pubsub_service import RedisPubSubService
from .streaming.router import router as streaming_router

from .inference.router import router as inference_router

from .matchtable.router import router as matchtable_router

# Instantiate supporting services
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager for startup/shutdown logic.
    """
    logger.info("Starting up API Gateway...")

    redis_client = RedisClientFactory.create_instance()

    app.state.pubsub_service = RedisPubSubService(redis_client=redis_client)

    logger.info("API Gateway startup complete")

    try:
        yield

    finally:  # Guarantee proper shut down from unexpected errors
        # Close Redis connection
        logger.info("Shutting down API Gateway...")
        await RedisClientFactory.close_instance()

    logger.info("API Gateway shutdown complete")


# Instantiate the app
app = FastAPI(title="Dota Oracle API Gateway", version="0.1.0", lifespan=lifespan)


# App configurations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inference_router)
app.include_router(matchtable_router)
app.include_router(streaming_router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

    """
    For Production:
    CMD: gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app -b 0.0.0.0:8000
    """
