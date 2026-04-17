"""
Repository-related fixtures for tests.
"""

import pytest
import pytest_asyncio
from unittest.mock import create_autospec
from sqlalchemy.ext.asyncio import AsyncSession

# Repository imports
from dota_oracle_common.repositories.heroes_repository import HeroesRepository
from dota_oracle_common.repositories.features_repository import FeaturesRepository
from dota_oracle_common.repositories.history_repository import HistoryRepository
from dota_oracle_common.repositories.match_repository import MatchRepository
from dota_oracle_common.repositories.prediction_repository import PredictionRepository
from dota_oracle_common.repositories.patch_repository import PatchRepository

# Test base classes
from ..integration.repositories.base_test_repository import BaseTestRepository
from ..integration.repositories.test_history_repository.base_history_repo import BaseHistoryRepositoryTest


# ================================
# REPOSITORY MOCKS
# ================================


@pytest.fixture
def mock_match_repository() -> MatchRepository:
    """
    Provides a high-fidelity mock of the MatchRepository.

    Using create_autospec ensures that the mock has the same methods and
    signatures as the real class, and correctly handles async methods.
    """
    return create_autospec(MatchRepository, instance=True)


@pytest.fixture
def mock_features_repository() -> FeaturesRepository:
    """
    Provides a high-fidelity mock of the FeaturesRepository.

    Using create_autospec ensures that the mock has the same methods and
    signatures as the real class, and correctly handles async methods.
    """
    return create_autospec(FeaturesRepository, instance=True)


@pytest.fixture
def mock_heroes_repository() -> HeroesRepository:
    """
    Provides a high-fidelity mock of the HeroesRepository.

    Using create_autospec ensures that the mock has the same methods and
    signatures as the real class, and correctly handles async methods.
    """
    return create_autospec(HeroesRepository, instance=True)


@pytest.fixture
def mock_history_repository() -> HistoryRepository:
    """
    Provides a high-fidelity mock of the HistoryRepository.

    Using create_autospec ensures that the mock has the same methods and
    signatures as the real class, and correctly handles async methods.
    """
    return create_autospec(HistoryRepository, instance=True)


@pytest.fixture
def mock_prediction_repository() -> PredictionRepository:
    """
    Provides a high-fidelity mock of the PredictionRepository.

    Using create_autospec ensures that the mock has the same methods and
    signatures as the real class, and correctly handles async methods.
    """
    return create_autospec(PredictionRepository, instance=True)


@pytest.fixture
def mock_patch_repository() -> PatchRepository:
    """
    Provides a high-fidelity mock of the PatchRepository.

    Using create_autospec ensures that the mock has the same methods and
    signatures as the real class, and correctly handles async methods.
    """
    return create_autospec(PatchRepository, instance=True)


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


@pytest_asyncio.fixture(scope="function")
async def hero_repository_test_subject(db_session: AsyncSession) -> HeroesRepository:
    return HeroesRepository(session=db_session)


@pytest_asyncio.fixture(scope="function")
async def history_repository_test_subject(db_session: AsyncSession) -> HistoryRepository:
    """Create HistoryRepository instance for testing."""
    return HistoryRepository(session=db_session)


@pytest_asyncio.fixture(scope="function")
async def match_repository_test_subject(db_session: AsyncSession):
    return MatchRepository(session=db_session)


@pytest_asyncio.fixture(scope="function")
async def patch_repository_test_subject(db_session: AsyncSession) -> PatchRepository:
    return PatchRepository(session=db_session)
