"""
Tests for get operations: get_player_hero_win_history, get_team_history, get_team_matchup_history
"""
import pytest
from typing import List
from datetime import datetime, timezone

from dota_oracle.data_repository.history_repository import HistoryRepository
from .base_history_repo import BaseHistoryRepositoryTest

pytestmark = pytest.mark.asyncio(loop_scope='session')


class TestGetPlayerHeroWinHistory:
    """Test retrieving player hero win history with various filters."""
    
    @pytest.mark.parametrize(
        "test_scenario,account_id,hero_id,before,limit,expected_win_history",
        [
            (
                "get_account1_hero10_limit4_no_filter",
                1,
                10,
                None,
                4,
                [False, False, True, True],  # Most recent first
            ),
            (
                "get_account1_hero10_with_before_filter",
                1, 
                10,
                datetime(2023, 1, 4, tzinfo=timezone.utc),
                10,
                [True, True, True]  # Before 2023-1-4, so matches 1001-1003
            ),
            (
                "get_nonexistent_hero_returns_empty",
                1,
                35,  # Hero that doesn't exist in seed data
                None,
                5,
                []
            ),
            (
                "get_nonexistent_account_returns_empty",
                99,  # Account that doesn't exist in seed data
                10,
                None,
                5,
                []
            )
        ]
    )
    async def test_get_player_hero_win_history_scenarios(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
        test_scenario: str,
        account_id: int,
        hero_id: int,
        before: datetime,
        limit: int,
        expected_win_history: List[bool]
    ):
        """Test various scenarios for getting player hero win history."""
        # Act
        actual_win_history = await history_repository_test_subject.get_player_hero_win_history(
            account_id=account_id, 
            hero_id=hero_id, 
            before=before, 
            limit=limit
        )
        
        # Assert
        history_test_repository._assert_win_history_equals(expected_win_history, actual_win_history, test_scenario)
    
    

class TestGetTeamHistory:
    """Test retrieving team history with various filters."""
    
    @pytest.mark.parametrize(
        "test_scenario,team_name,before,limit,expected_win_history",
        [
            (
                "get_team_secret_limit5_no_filter",
                "team_secret",
                None,
                5,
                [True, True, False, False, True],  # Most recent first: 1005,1004,1003,1002,1001
            ),
            (
                "get_team_secret_with_before_filter",
                "team_secret",
                datetime(2023, 1, 3, tzinfo=timezone.utc),
                5,
                [False, True]  # Before 2023-1-3, so matches 1002,1001
            ),
            (
                "get_nonexistent_team_returns_empty",
                "team_spirit",  # Team that doesn't exist in seed data
                None,
                5,
                []
            ),
            (
                "get_existing_team_psg_lgd",
                "PSG_LGD",
                None,
                5,
                [True]  # Only one match in seed data
            )
        ]
    )
    async def test_get_team_history_scenarios(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
        test_scenario: str,
        team_name: str,
        before: datetime,
        limit: int,
        expected_win_history: List[bool]
    ):
        """Test various scenarios for getting team history."""
        # Act
        actual_win_history = await history_repository_test_subject.get_team_history(
            team_name=team_name, 
            before=before, 
            limit=limit
        )
        
        # Assert
        history_test_repository._assert_win_history_equals(expected_win_history, actual_win_history, test_scenario)
    
    

class TestGetOperationsEmptyDatabase:
    async def test_get_team_history_empty_database(
        self,
        history_repository_test_subject: HistoryRepository,
    ):
        """Test that empty database returns empty list."""
        # Act
        result = await history_repository_test_subject.get_team_history(
            team_name="team_secret", before=None, limit=5
        )
        
        # Assert
        assert result == [], "Expected empty list for empty database"
        
    async def test_get_player_hero_win_history_empty_database(
        self,
        history_repository_test_subject: HistoryRepository,
    ):
        """Test that empty database returns empty list."""
        # Act
        result = await history_repository_test_subject.get_player_hero_win_history(
            account_id=1, hero_id=10, before=None, limit=5
        )
        
        # Assert
        assert result == [], "Expected empty list for empty database"
        
    async def test_get_team_matchup_history_empty_database(
        self,
        history_repository_test_subject: HistoryRepository,
    ):
        """Test that empty database returns empty list."""
        # Act
        result = await history_repository_test_subject.get_team_matchup_history(
            team_one="team_secret", team_two="PSG_LGD", before=None, limit=5
        )
        
        # Assert
        assert result == [], "Expected empty list for empty database"
        
    
class TestGetTeamMatchupHistory:
    """Test retrieving team matchup history with various filters."""
    
    @pytest.mark.parametrize(
        "test_scenario,team1_name,team2_name,before,limit,expected_win_history",
        [
            (
                "get_team_secret_vs_psg_lgd_limit5",
                "team_secret",
                "PSG_LGD",
                None,
                5,
                [False, True, False, True, True]
            ),
            (
                "test_team_order_independence",
                "PSG_LGD",
                "team_secret", 
                None,
                5,
                [True, False, True, False, False],  # Same matchup, same results
            ),
            (
                "get_matchup_with_before_filter",
                "team_secret",
                "PSG_LGD",
                datetime(2023, 1, 3, tzinfo=timezone.utc),
                5,
                [True, True]  # Before 2023-1-3, so matches 1002,1001
            ),
            (
                "get_nonexistent_team_matchup_returns_empty",
                "team_spirit",
                "team_secret",
                None,
                10,
                []
            ),
            (
                "get_nonexistent_team2_matchup_returns_empty",
                "team_secret",
                "team_spirit",
                None,
                10,
                []
            )
        ]
    )
    async def test_get_team_matchup_history_scenarios(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
        test_scenario: str,
        team1_name: str,
        team2_name: str,
        before: datetime,
        limit: int,
        expected_win_history: List[bool]
    ):
        """Test various scenarios for getting team matchup history."""
        # Act
        actual_win_history = await history_repository_test_subject.get_team_matchup_history(
            team_one=team1_name, 
            team_two=team2_name, 
            before=before, 
            limit=limit
        )
        
        # Assert
        history_test_repository._assert_win_history_equals(expected_win_history, actual_win_history, test_scenario)
    
    
    async def test_team_order_independence(
        self,
        history_repository_test_subject: HistoryRepository,
    ):
        """Test that team order doesn't matter for matchup history."""
        # Act - Get matchup in both orders
        result1 = await history_repository_test_subject.get_team_matchup_history(
            team_one="team_secret", team_two="PSG_LGD", before=None, limit=5
        )
        result2 = await history_repository_test_subject.get_team_matchup_history(
            team_one="PSG_LGD", team_two="team_secret", before=None, limit=5
        )
        
        # Assert - Results should be identical
        assert result1 == result2, (
            f"Team order should not matter: {result1} vs {result2}"
        )