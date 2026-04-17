import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from dota_oracle_common.utils import get_logger
from dota_oracle_common.models.patches.table import PatchTable

from typing import List

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(scope="function")
async def seed_patch_data(db_session: AsyncSession, patch_table_factory) -> List[PatchTable]:
    PATCH_DATA = [
        patch_table_factory.build(
            id=101,
            patch_number="7.35",
            start_time=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
        ),
        patch_table_factory.build(
            id=102,
            patch_number="7.36",
            start_time=datetime(2024, 3, 1, tzinfo=timezone.utc),
            end_time=datetime(2024, 6, 1, tzinfo=timezone.utc),
        ),
        patch_table_factory.build(
            id=103,
            patch_number="7.37",
            start_time=datetime(2024, 6, 1, tzinfo=timezone.utc),
            end_time=None,  # Latest patch
        ),
    ]

    db_session.add_all(PATCH_DATA)
    await db_session.flush()

    logger.info(f"Successfully seeded {len(PATCH_DATA)} patch records")

    return PATCH_DATA
