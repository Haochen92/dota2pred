"""
Tests for add operations: add_player_hero_match_outcome, add_team_match_outcome, add_team_match_up_outcome
"""
import pytest
from typing import Optional
from datetime import datetime, timezone

from dota_oracle.data_repository.history_repository import HistoryRepository
from .conftest import BaseHistoryRepositoryTest

pytestmark = pytest.mark.asyncio(loop_scope='session')


@pytest.mark.usefixtures("seed_history_data")
class TestAddPlayerHeroMatchOutcome(BaseHistoryRepositoryTest):
    """Test adding player hero match outcomes with conflict handling."""
    
    @pytest.mark.parametrize(
        "test_scenario,account_id,hero_id,match_id,win,start_time,expected_count,expected_win,expected_start_time",
        [
            (
                "add_new_player_hero_outcome_successfully",
                3,  # New account_id
                10,
                1003,
                True,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                1,  # Should create 1 new record
                True,  # Should have our input win value
                datetime(2025, 1, 1, tzinfo=timezone.utc)  # Should have our input time
            ),
            (
                "conflict_preserves_original_data",
                1,  # Existing account_id from seed data
                10, # Existing hero_id from seed data
                1001, # Existing match_id from seed data
                False,  # Try to insert different win value
                datetime(2025, 1, 1, tzinfo=timezone.utc),  # Try to insert different time
                1,  # Should still have 1 record (the original)
                True,  # Should keep original win value from seed data
                datetime(2023, 1, 1, tzinfo=timezone.utc)  # Should keep original time from seed data
            ),
            (
                "add_same_account_hero_different_match",
                1,  # Existing account_id
                10, # Existing hero_id
                9999, # New match_id
                False,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                1,  # Should create 1 new record
                False, # Should have our input win value
                datetime(2025, 1, 1, tzinfo=timezone.utc) # Should have our input time
            )
        ]
    )
    async def test_add_player_hero_match_outcome_scenarios(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine,
        test_scenario: str,
        account_id: int,
        hero_id: int,
        match_id: int,
        win: bool,
        start_time: datetime,
        expected_count: int,
        expected_win: bool,
        expected_start_time: datetime,
    ):
        """Test various scenarios for adding player hero match outcomes."""
        # Act
        await history_repository_test_subject.add_player_hero_match_outcome(
            account_id=account_id,
            hero_id=hero_id,
            match_id=match_id,
            win=win,
            match_start_time=start_time
        )
        
        # Assert
        records = await self._get_player_hero_records(
            test_postgres_engine, account_id, hero_id, match_id
        )
        
        self._assert_record_count_equals(expected_count, records, test_scenario)
        
        if expected_count > 0:
            record = records[0]
            self._assert_player_hero_record_equals(
                record, account_id, hero_id, match_id, 
                expected_win, expected_start_time, test_scenario
            )
    
    async def test_add_player_hero_outcome_empty_database(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine,
        empty_history_database  # Inject fixture as parameter
    ):
        """Test adding player hero outcome to empty database."""
        # Arrange
        account_id, hero_id, match_id = 1, 10, 1001
        win = True
        start_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        
        # Act
        await history_repository_test_subject.add_player_hero_match_outcome(
            account_id=account_id,
            hero_id=hero_id,
            match_id=match_id,
            win=win,
            match_start_time=start_time
        )
        
        # Assert
        records = await self._get_player_hero_records(
            test_postgres_engine, account_id, hero_id, match_id
        )
        
        assert len(records) == 1, "Expected 1 record in empty database"
        self._assert_player_hero_record_equals(
            records[0], account_id, hero_id, match_id, win, start_time, "Empty database test"
        )


@pytest.mark.usefixtures("seed_history_data")
class TestAddTeamMatchOutcome(BaseHistoryRepositoryTest):
    """Test adding team match outcomes with conflict handling."""
    
    @pytest.mark.parametrize(
        "test_scenario,team_name,match_id,win,start_time,expected_count,expected_win,expected_start_time",
        [
            (
                "add_new_team_match_outcome_successfully",
                "liquid",  # New team not in seed data
                3001,
                True,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                1,  # Should create 1 new record
                True,  # Should have our input win value
                datetime(2025, 1, 1, tzinfo=timezone.utc)  # Should have our input time
            ),
            (
                "conflict_preserves_original_team_data",
                "team_secret",  # Existing team from seed data
                1001,  # Existing match_id from seed data
                False,  # Try to insert different win value
                datetime(2025, 1, 1, tzinfo=timezone.utc),  # Try to insert different time
                1,  # Should still have 1 record (the original)
                True,  # Should keep original win value from seed data
                datetime(2023, 1, 1, tzinfo=timezone.utc)  # Should keep original time from seed data
            ),
            (
                "add_existing_team_new_match",
                "team_secret",  # Existing team
                9999,  # New match_id
                False,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                1,  # Should create 1 new record
                False,  # Should have our input win value
                datetime(2025, 1, 1, tzinfo=timezone.utc)  # Should have our input time
            )
        ]
    )
    async def test_add_team_match_outcome_scenarios(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine,
        test_scenario: str,
        team_name: str,
        match_id: int,
        win: bool,
        start_time: datetime,
        expected_count: int,
        expected_win: bool,
        expected_start_time: datetime,
    ):
        """Test various scenarios for adding team match outcomes."""
        # Act
        await history_repository_test_subject.add_team_match_outcome(
            team_name=team_name,
            match_id=match_id,
            win=win,
            match_start_time=start_time
        )
        
        # Assert
        records = await self._get_team_history_records(
            test_postgres_engine, team_name, match_id
        )
        
        self._assert_record_count_equals(expected_count, records, test_scenario)
        
        if expected_count > 0:
            record = records[0]
            self._assert_team_history_record_equals(
                record, team_name, match_id, expected_win, expected_start_time, test_scenario
            )


@pytest.mark.usefixtures("seed_history_data")
class TestAddTeamMatchUpOutcome(BaseHistoryRepositoryTest):
    """Test adding team matchup outcomes with conflict handling and team sorting."""
    
    @pytest.mark.parametrize(
        "test_scenario,team_one,team_two,match_id,win,start_time,expected_count,expected_team1,expected_team2,expected_win,expected_start_time",
        [
            (
                "add_new_matchup_successfully",
                "liquid",
                "navi",  # Sorted will be: liquid, navi
                3001,
                True,  # liquid wins
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                1,  # Should create 1 new record
                "liquid",  # Sorted team1_name
                "navi",    # Sorted team2_name
                True,      # Should have our input win value
                datetime(2025, 1, 1, tzinfo=timezone.utc)  # Should have our input time
            ),
            (
                "conflict_preserves_original_matchup_data",
                "team_secret",
                "PSG_LGD",  # Sorted will be: PSG_LGD, team_secret (matches seed data)
                1001,  # This should already exist in seed data
                True,  # Try to insert different win value
                datetime(2025, 1, 1, tzinfo=timezone.utc),  # Try to insert different time
                1,  # Should still have 1 record (the original)
                "PSG_LGD",     # Sorted team1_name (matches seed data)
                "team_secret", # Sorted team2_name (matches seed data)
                False,  # Should keep original win value from seed data
                datetime(2023, 1, 1, tzinfo=timezone.utc)  # Should keep original time from seed data
            ),
            (
                "team_order_independence_existing_match",
                "PSG_LGD",
                "team_secret",  # Even though order is different, should sort to same as above
                1002,  # Different match_id from seed data
                False,  # PSG_LGD loses (team_secret wins)
                datetime(2025, 1, 2, tzinfo=timezone.utc),
                1,  # Should still have 1 record (the original with match_id 1002)
                "PSG_LGD",     # Sorted team1_name
                "team_secret", # Sorted team2_name
                False,  # Should keep original win value from seed data (PSG_LGD loses)
                datetime(2023, 1, 2, tzinfo=timezone.utc)  # Should keep original time from seed data
            ),
            (
                "team_order_independence_new_match",
                "liquid",
                "alliance",  # Will be sorted to: alliance, liquid
                3002,
                False,  # liquid loses (alliance wins)
                datetime(2025, 1, 3, tzinfo=timezone.utc),
                1,  # Should create 1 new record
                "alliance",  # Sorted team1_name
                "liquid",    # Sorted team2_name
                False,       # liquid loses (alliance wins)
                datetime(2025, 1, 3, tzinfo=timezone.utc)
            )
        ]
    )
    async def test_add_team_matchup_outcome_scenarios(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine,
        test_scenario: str,
        team_one: str,
        team_two: str,
        match_id: int,
        win: bool,
        start_time: datetime,
        expected_count: int,
        expected_team1: str,
        expected_team2: str,
        expected_win: bool,
        expected_start_time: datetime,
    ):
        """Test various scenarios for adding team matchup outcomes."""
        # Act
        await history_repository_test_subject.add_team_match_up_outcome(
            team_one=team_one,
            team_two=team_two,
            match_id=match_id,
            win=win,
            match_start_time=start_time
        )
        
        # Assert
        records = await self._get_team_matchup_records(
            test_postgres_engine, expected_team1, expected_team2, match_id
        )
        
        self._assert_record_count_equals(expected_count, records, test_scenario)
        
        if expected_count > 0:
            record = records[0]
            self._assert_team_matchup_record_equals(
                record, expected_team1, expected_team2, match_id, 
                expected_win, expected_start_time, test_scenario
            )
    
    @pytest.mark.parametrize(
        "test_scenario,team_one,team_two,match_id,win,start_time,expected_count",
        [
            (
                "empty_team_one_creates_no_record",
                None,  # Empty team_one
                "team_secret",
                4001,
                True,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                0,  # Should not create any record
            ),
            (
                "empty_team_two_creates_no_record",
                "team_secret",
                None,  # Empty team_two
                4002,
                True,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                0,  # Should not create any record
            ),
            (
                "both_teams_empty_creates_no_record",
                None,
                None,
                4003,
                True,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
                0,  # Should not create any record
            ),
        ]
    )
    async def test_add_team_matchup_outcome_edge_cases(
        self,
        history_repository_test_subject: HistoryRepository,
        test_postgres_engine,
        test_scenario: str,
        team_one: Optional[str],
        team_two: Optional[str],
        match_id: int,
        win: bool,
        start_time: datetime,
        expected_count: int,
    ):
        """Test edge cases for adding team matchup outcomes."""
        # Act
        await history_repository_test_subject.add_team_match_up_outcome(
            team_one=team_one,
            team_two=team_two,
            match_id=match_id,
            win=win,
            match_start_time=start_time
        )
        
        # Assert - Verify no records were created for the specific match_id
        from sqlmodel import select
        from sqlalchemy.ext.asyncio import AsyncSession
        from dota_oracle.data_repository.schemas import TeamMatchupHistoryTable
        
        async with AsyncSession(test_postgres_engine) as session:
            stmt = select(TeamMatchupHistoryTable).where(TeamMatchupHistoryTable.match_id == match_id)
            result = await session.execute(stmt)
            records = result.scalars().all()
            
            assert len(records) == expected_count, (
                f"{test_scenario}: Expected {expected_count} records for match_id {match_id}, "
                f"but found {len(records)}"
            )