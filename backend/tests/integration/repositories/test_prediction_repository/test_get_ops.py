import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import delete, select

from ....factories.repository_factories import MatchPredictionTableFactory
from dota_oracle.data_repository.schemas import MatchPredictionTable
from dota_oracle.data_repository.prediction_repository import PredictionRepository


from typing import List, Tuple, Any, AsyncGenerator, Dict, Set

from dota_oracle.utils.set_logging import get_logger

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')