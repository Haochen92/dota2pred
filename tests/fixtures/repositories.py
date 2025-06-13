"""
Repository-related fixtures for tests.
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Repository imports
from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.repositories.prediction_repository import PredictionRepository

# Test base classes
from ..integration.repositories.base_test_repository import BaseTestRepository
from ..integration.repositories.test_history_repository.base_history_repo import BaseHistoryRepositoryTest


# ================================
# REPOSITORY MOCKS
# ================================

@pytest.fixture
def mock_match_repository() -> MatchRepository:
    return AsyncMock(spec=MatchRepository)


@pytest.fixture
def mock_features_repository() -> FeaturesRepository:
    return AsyncMock(spec=FeaturesRepository)


@pytest.fixture
def mock_heroes_repository() -> HeroesRepository:
    return AsyncMock(spec=HeroesRepository)


@pytest.fixture
def mock_history_repository() -> HistoryRepository:
    return AsyncMock(spec=HistoryRepository)


@pytest.fixture
def mock_prediction_repository() -> PredictionRepository:
    return AsyncMock(spec=PredictionRepository)


# ================================
# REPOSITORY TEST SUBJECTS
# ================================

@pytest_asyncio.fixture(scope="function")
async def test_repository(db_session: AsyncSession) -> BaseTestRepository:
    return BaseTestRepository(session=db_session)


@pytest_asyncio.fixture(scope="function")
async def history_test_repository(db_session: AsyncSession) -> BaseHistoryRepositoryTest:
    """Create BaseHistoryRepositoryTest instance for history repository testing."""
    return BaseHistoryRepositoryTest(session=db_session)



@pytest_asyncio.fixture(scope="function")
async def features_repository_test_subject(db_session: AsyncSession) -> FeaturesRepository:
    """Create FeaturesRepository instance for testing."""
    return FeaturesRepository(session=db_session)


@pytest_asyncio.fixture(scope='function')
async def hero_repository_test_subject(db_session: AsyncSession) -> HeroesRepository:
    return HeroesRepository(session=db_session)


@pytest_asyncio.fixture(scope="function")
async def history_repository_test_subject(db_session: AsyncSession) -> HistoryRepository:
    """Create HistoryRepository instance for testing."""
    return HistoryRepository(session=db_session)


@pytest_asyncio.fixture(scope='function')
async def match_repository_test_subject(db_session: AsyncSession):
    return MatchRepository(session=db_session)