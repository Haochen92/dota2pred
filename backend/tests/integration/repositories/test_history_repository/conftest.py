"""
Shared fixtures and base classes for history repository tests.
"""
import pytest
import pytest_asyncio
from typing import List, Optional, Any, Set
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import delete
from sqlmodel import select
from datetime import datetime, timezone

from dota_oracle.data_repository.schemas import TeamHistoryTable, PlayerHeroHistoryTable, TeamMatchupHistoryTable
from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.utils.set_logging import get_logger

from ....factories.repository_factories import TeamHistoryTableFactory, PlayerHeroHistoryTableFactory, TeamMatchupHistoryTableFactory

logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope='session')


class BaseHistoryRepositoryTest:
    """Base class with common assertion helpers and database operations for history repository tests."""
    
    # Database Operation Helpers
    async def _get_player_hero_records(
        self, 
        engine: AsyncEngine, 
        account_id: int, 
        hero_id: int, 
        match_id: int = None
    ) -> List[PlayerHeroHistoryTable]:
        """Retrieve player hero history records."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(PlayerHeroHistoryTable).where(
                    PlayerHeroHistoryTable.account_id == account_id,
                    PlayerHeroHistoryTable.hero_id == hero_id
                )
                if match_id is not None:
                    stmt = stmt.where(PlayerHeroHistoryTable.match_id == match_id)
                
                result = await session.execute(stmt)
                records = result.scalars().all()
                session.expunge_all()
                return records
    
    async def _get_team_history_records(
        self, 
        engine: AsyncEngine, 
        team_name: str, 
        match_id: int = None
    ) -> List[TeamHistoryTable]:
        """Retrieve team history records."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(TeamHistoryTable).where(TeamHistoryTable.team_name == team_name)
                if match_id is not None:
                    stmt = stmt.where(TeamHistoryTable.match_id == match_id)
                
                result = await session.execute(stmt)
                records = result.scalars().all()
                session.expunge_all()
                return records
    
    async def _get_team_matchup_records(
        self, 
        engine: AsyncEngine, 
        team1_name: str, 
        team2_name: str, 
        match_id: int = None
    ) -> List[TeamMatchupHistoryTable]:
        """Retrieve team matchup history records."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(TeamMatchupHistoryTable).where(
                    TeamMatchupHistoryTable.team1_name == team1_name,
                    TeamMatchupHistoryTable.team2_name == team2_name
                )
                if match_id is not None:
                    stmt = stmt.where(TeamMatchupHistoryTable.match_id == match_id)
                
                result = await session.execute(stmt)
                records = result.scalars().all()
                session.expunge_all()
                return records
    
    async def _count_records_in_table(self, engine: AsyncEngine, table_class: Any) -> int:
        """Count total records in a history table."""
        async with AsyncSession(engine) as session:
            async with session.begin():
                stmt = select(table_class)
                result = await session.execute(stmt)
                return len(result.scalars().all())
    
    # Assertion Helpers
    def _assert_win_history_equals(
        self, 
        expected_history: List[bool], 
        actual_history: List[bool], 
        context: str = ""
    ):
        """Assert that win history lists match exactly."""
        assert actual_history == expected_history, (
            f"{context} - Win history mismatch: "
            f"expected {expected_history}, got {actual_history}"
        )
    
    def _assert_record_count_equals(
        self, 
        expected_count: int, 
        actual_records: List[Any], 
        context: str = ""
    ):
        """Assert that record count matches expected."""
        actual_count = len(actual_records)
        assert actual_count == expected_count, (
            f"{context} - Record count mismatch: "
            f"expected {expected_count}, got {actual_count}"
        )
    
    def _assert_player_hero_record_equals(
        self, 
        record: PlayerHeroHistoryTable,
        expected_account_id: int,
        expected_hero_id: int,
        expected_match_id: int,
        expected_win: bool,
        expected_start_time: datetime,
        context: str = ""
    ):
        """Assert player hero record has expected values."""
        assert record.account_id == expected_account_id, (
            f"{context} - account_id mismatch: expected {expected_account_id}, got {record.account_id}"
        )
        assert record.hero_id == expected_hero_id, (
            f"{context} - hero_id mismatch: expected {expected_hero_id}, got {record.hero_id}"
        )
        assert record.match_id == expected_match_id, (
            f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        )
        assert record.win == expected_win, (
            f"{context} - win mismatch: expected {expected_win}, got {record.win}"
        )
        assert record.start_time == expected_start_time, (
            f"{context} - start_time mismatch: expected {expected_start_time}, got {record.start_time}"
        )
    
    def _assert_team_history_record_equals(
        self,
        record: TeamHistoryTable,
        expected_team_name: str,
        expected_match_id: int,
        expected_win: bool,
        expected_start_time: datetime,
        context: str = ""
    ):
        """Assert team history record has expected values."""
        assert record.team_name == expected_team_name, (
            f"{context} - team_name mismatch: expected {expected_team_name}, got {record.team_name}"
        )
        assert record.match_id == expected_match_id, (
            f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        )
        assert record.win == expected_win, (
            f"{context} - win mismatch: expected {expected_win}, got {record.win}"
        )
        assert record.start_time == expected_start_time, (
            f"{context} - start_time mismatch: expected {expected_start_time}, got {record.start_time}"
        )
    
    def _assert_team_matchup_record_equals(
        self,
        record: TeamMatchupHistoryTable,
        expected_team1_name: str,
        expected_team2_name: str,
        expected_match_id: int,
        expected_win: bool,
        expected_start_time: datetime,
        context: str = ""
    ):
        """Assert team matchup record has expected values."""
        assert record.team1_name == expected_team1_name, (
            f"{context} - team1_name mismatch: expected {expected_team1_name}, got {record.team1_name}"
        )
        assert record.team2_name == expected_team2_name, (
            f"{context} - team2_name mismatch: expected {expected_team2_name}, got {record.team2_name}"
        )
        assert record.match_id == expected_match_id, (
            f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        )
        assert record.win == expected_win, (
            f"{context} - win mismatch: expected {expected_win}, got {record.win}"
        )
        assert record.start_time == expected_start_time, (
            f"{context} - start_time mismatch: expected {expected_start_time}, got {record.start_time}"
        )


# ========================
# FIXTURES
# ========================

@pytest_asyncio.fixture(scope="function")
async def history_repository_test_subject(test_postgres_engine: AsyncEngine) -> HistoryRepository:
    """Create HistoryRepository instance for testing."""
    return HistoryRepository(engine=test_postgres_engine)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def auto_clear_history_database(test_postgres_engine: AsyncEngine):
    # Ensure clean state before each test
    logger.info("Setting up test by clearing database...")
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(PlayerHeroHistoryTable))
            await session.execute(delete(TeamHistoryTable))
            await session.execute(delete(TeamMatchupHistoryTable))
    
    logger.info("Clean database is set up")
    
    """Automatically clean up history tables after each test."""
    yield  # Let the test run first
    
    # Cleanup after test completes - always runs for every test
    logger.info("Auto-cleaning history tables...")
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            await session.execute(delete(PlayerHeroHistoryTable))
            await session.execute(delete(TeamHistoryTable))
            await session.execute(delete(TeamMatchupHistoryTable))
    
    logger.info("Auto history cleanup complete")


@pytest_asyncio.fixture(scope="function")
async def seed_history_data(test_postgres_engine: AsyncEngine):
    """Seeds data for history repository read operations tests."""
    
    logger.info("Seeding history data for read operations")
    
    player_hero_data = [
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=True, match_id=1001, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=True, match_id=1002, start_time=datetime(2023,1,2,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=True, match_id=1003, start_time=datetime(2023,1,3,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=False, match_id=1004, start_time=datetime(2023,1,4,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=1, hero_id=10, win=False, match_id=1005, start_time=datetime(2023,1,5,tzinfo=timezone.utc)),
        PlayerHeroHistoryTableFactory.build(account_id=2, hero_id=20, win=True, match_id=2001, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
    ]
    
    team_history_data = [
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1001, win=True, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1002, win=False, start_time=datetime(2023,1,2,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1003, win=False, start_time=datetime(2023,1,3,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1004, win=True, start_time=datetime(2023,1,4,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='team_secret', match_id=1005, win=True, start_time=datetime(2023,1,5,tzinfo=timezone.utc)),
        TeamHistoryTableFactory.build(team_name='PSG_LGD', match_id=2001, win=True, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
    ]
    
    team_match_up_data = [
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1001, win=False, start_time=datetime(2023,1,1,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1002, win=False, start_time=datetime(2023,1,2,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1003, win=True, start_time=datetime(2023,1,3,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1004, win=False, start_time=datetime(2023,1,4,tzinfo=timezone.utc)),
        TeamMatchupHistoryTableFactory.build(team1_name='PSG_LGD', team2_name='team_secret', match_id=1005, win=True, start_time=datetime(2023,1,5,tzinfo=timezone.utc)),  
    ]
    
    async with AsyncSession(test_postgres_engine) as session:
        async with session.begin():
            all_data = player_hero_data + team_history_data + team_match_up_data
            for instance in all_data:
                session.add(instance)
            
        logger.info(f"History seeding complete.")

    yield
    
    # This fixture's cleanup is handled by auto_clear_history_database
    logger.info("Seed history data fixture completed")
