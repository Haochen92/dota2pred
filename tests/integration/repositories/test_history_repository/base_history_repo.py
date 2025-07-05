from typing import List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from sqlmodel import select


from dota_oracle_common.models.histories import TeamHistoryTable, PlayerHeroHistoryTable, TeamMatchupHistoryTable
from dota_oracle_common.utils.set_logging import get_logger

from datetime import datetime


logger = get_logger(__name__)


class BaseHistoryRepositoryTest:
    """Base class with common assertion helpers and database operations for history repository tests."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Database Operation Helpers
    async def _get_player_hero_records(
        self, account_id: int, hero_id: int, match_id: Optional[int] = None
    ) -> List[PlayerHeroHistoryTable]:
        """Retrieve player hero history records."""

        stmt = select(PlayerHeroHistoryTable).where(
            PlayerHeroHistoryTable.account_id == account_id, PlayerHeroHistoryTable.hero_id == hero_id
        )
        if match_id is not None:
            stmt = stmt.where(PlayerHeroHistoryTable.match_id == match_id)

        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return list(records)

    async def _get_team_history_records(self, team_name: str, match_id: Optional[int] = None) -> List[TeamHistoryTable]:
        """Retrieve team history records."""

        stmt = select(TeamHistoryTable).where(TeamHistoryTable.team_name == team_name)
        if match_id is not None:
            stmt = stmt.where(TeamHistoryTable.match_id == match_id)

        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return list(records)

    async def _get_team_matchup_records(
        self, team1_name: str, team2_name: str, match_id: Optional[int] = None
    ) -> List[TeamMatchupHistoryTable]:
        """Retrieve team matchup history records."""
        stmt = select(TeamMatchupHistoryTable).where(
            TeamMatchupHistoryTable.team1_name == team1_name, TeamMatchupHistoryTable.team2_name == team2_name
        )
        if match_id is not None:
            stmt = stmt.where(TeamMatchupHistoryTable.match_id == match_id)

        result = await self.session.execute(stmt)
        records = result.scalars().all()

        return list(records)

    async def _count_records_in_table(self, table_class: Any) -> int:
        """Count total records in a history table."""
        stmt = select(table_class)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    # Assertion Helpers
    def _assert_win_history_equals(self, expected_history: List[bool], actual_history: List[bool], context: str = ""):
        """Assert that win history lists match exactly."""
        assert actual_history == expected_history, (
            f"{context} - Win history mismatch: " f"expected {expected_history}, got {actual_history}"
        )

    def _assert_record_count_equals(self, expected_count: int, actual_records: List[Any], context: str = ""):
        """Assert that record count matches expected."""
        actual_count = len(actual_records)
        assert actual_count == expected_count, (
            f"{context} - Record count mismatch: " f"expected {expected_count}, got {actual_count}"
        )

    def _assert_player_hero_record_equals(
        self,
        record: PlayerHeroHistoryTable,
        expected_account_id: int,
        expected_hero_id: int,
        expected_match_id: int,
        expected_win: bool,
        expected_start_time: datetime,
        context: str = "",
    ):
        """Assert player hero record has expected values."""
        assert (
            record.account_id == expected_account_id
        ), f"{context} - account_id mismatch: expected {expected_account_id}, got {record.account_id}"
        assert (
            record.hero_id == expected_hero_id
        ), f"{context} - hero_id mismatch: expected {expected_hero_id}, got {record.hero_id}"
        assert (
            record.match_id == expected_match_id
        ), f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        assert record.win == expected_win, f"{context} - win mismatch: expected {expected_win}, got {record.win}"
        assert (
            record.start_time == expected_start_time
        ), f"{context} - start_time mismatch: expected {expected_start_time}, got {record.start_time}"

    def _assert_team_history_record_equals(
        self,
        record: TeamHistoryTable,
        expected_team_name: str,
        expected_match_id: int,
        expected_win: bool,
        expected_start_time: datetime,
        context: str = "",
    ):
        """Assert team history record has expected values."""
        assert (
            record.team_name == expected_team_name
        ), f"{context} - team_name mismatch: expected {expected_team_name}, got {record.team_name}"
        assert (
            record.match_id == expected_match_id
        ), f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        assert record.win == expected_win, f"{context} - win mismatch: expected {expected_win}, got {record.win}"
        assert (
            record.start_time == expected_start_time
        ), f"{context} - start_time mismatch: expected {expected_start_time}, got {record.start_time}"

    def _assert_team_matchup_record_equals(
        self,
        record: TeamMatchupHistoryTable,
        expected_team1_name: str,
        expected_team2_name: str,
        expected_match_id: int,
        expected_win: bool,
        expected_start_time: datetime,
        context: str = "",
    ):
        """Assert team matchup record has expected values."""
        assert (
            record.team1_name == expected_team1_name
        ), f"{context} - team1_name mismatch: expected {expected_team1_name}, got {record.team1_name}"
        assert (
            record.team2_name == expected_team2_name
        ), f"{context} - team2_name mismatch: expected {expected_team2_name}, got {record.team2_name}"
        assert (
            record.match_id == expected_match_id
        ), f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        assert record.win == expected_win, f"{context} - win mismatch: expected {expected_win}, got {record.win}"
        assert (
            record.start_time == expected_start_time
        ), f"{context} - start_time mismatch: expected {expected_start_time}, got {record.start_time}"
