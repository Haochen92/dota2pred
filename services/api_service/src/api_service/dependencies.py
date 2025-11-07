# your_app/dependencies.py

from typing import Annotated, AsyncGenerator, Dict
import httpx
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# --- Import Services and Repositories ---
from dota_oracle_common.repositories.patch_repository import PatchRepository
from .streaming.redis_pubsub_service import RedisPubSubService
from .matches.match_pagination_service import MatchPaginationService
from .inference.model_history_service import ModelHistoryService
from .inference.pub_inference import PubInferenceService
from .inference.prediction_details_service import PredictionDetailsService


# === Dependency Provider Functions ===
# These functions define HOW to get a dependency. They typically retrieve
# pre-initialized objects from the application state (request.app.state).


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Provides the shared httpx.AsyncClient connection pool."""
    return request.app.state.http_client


def get_pubsub_service(request: Request) -> RedisPubSubService:
    """Provides the shared RedisPubSubService instance."""
    return request.app.state.pubsub_service


def get_public_inference_service(request: Request) -> PubInferenceService:
    """Provides the shared PubInferenceService instance."""
    return request.app.state.public_inference_service


def get_hero_map(request: Request) -> Dict[int, str]:
    """Provides the shared hero map."""
    return request.app.state.hero_map


async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Provides a database session with automatic transaction management.
    Commits on success, rolls back on failure.
    """
    session_factory = request.app.state.db_session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_match_pagination_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
    hero_map: Annotated[Dict[int, str], Depends(get_hero_map)],
) -> MatchPaginationService:
    """
    Creates a new MatchPaginationService instance for a single request,
    injecting it with a database session and its required repositories.
    """
    return MatchPaginationService(
        db_session=db_session, patch_repository=PatchRepository(db_session), hero_map=hero_map
    )


def get_model_history_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ModelHistoryService:
    """
    Creates a new ModelHistoryService instance for a single request,
    injecting it with a database session.
    """
    return ModelHistoryService(db_session=db_session)


def get_prediction_details_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> PredictionDetailsService:
    """
    Creates a new PredictionDetailsService instance for a single request,
    injecting it with a database session.
    """
    return PredictionDetailsService(db_session=db_session)


# === Dependency Aliases ===
# These provide clean, reusable, and type-hinted shortcuts for use in route signatures.
# This makes endpoint functions declarative and easy to read.

HTTPClient = Annotated[httpx.AsyncClient, Depends(get_http_client)]
PubSub = Annotated[RedisPubSubService, Depends(get_pubsub_service)]
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
InferenceSvc = Annotated[PubInferenceService, Depends(get_public_inference_service)]
MatchPaginationSvc = Annotated[MatchPaginationService, Depends(get_match_pagination_service)]
ModelHistorySvc = Annotated[ModelHistoryService, Depends(get_model_history_service)]
PredictionDetailsSvc = Annotated[PredictionDetailsService, Depends(get_prediction_details_service)]
HeroMap = Annotated[Dict[int, str], Depends(get_hero_map)]
