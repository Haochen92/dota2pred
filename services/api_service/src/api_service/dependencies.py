from typing import Annotated, AsyncGenerator
from fastapi import Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.repositories.patch_repository import PatchRepository
from .streaming.redis_pubsub_service import RedisPubSubService
from .matches.match_pagination_service import MatchPaginationService


# Dependency Providers
def get_pubsub_service(request: Request) -> RedisPubSubService:
    return request.app.state.pubsub_service


async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session with proper transaction handling.
    """
    session_factory = request.app.state.db_session_factory

    async with session_factory() as session:
        try:
            # Yield the session to the route/service layer
            yield session
            # If the request was successful, commit the transaction
            await session.commit()
        except Exception:
            # If any exception occurred, roll back the transaction
            await session.rollback()
            # Re-raise the exception to be handled by FastAPI's error handling
            raise


def get_match_pagination_service(
    db_session: Annotated[AsyncSession, Depends(get_database_session)],
) -> MatchPaginationService:
    """Create MatchPaginationService with all its repository dependencies."""
    hero_repo = HeroesRepository(db_session)
    patch_repo = PatchRepository(db_session)
    return MatchPaginationService(
        db_session=db_session,
        hero_repository=hero_repo,
        patch_repository=patch_repo,
    )


# Dependency Aliases
PubSub = Annotated[RedisPubSubService, Depends(get_pubsub_service)]
DatabaseSession = Annotated[AsyncSession, Depends(get_database_session)]
MatchPaginationSvc = Annotated[MatchPaginationService, Depends(get_match_pagination_service)]
