from typing import List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from sqlmodel import select

from dota_oracle_common.models.histories import (
    HeroDecayedStateTable,
    PlayerHeroDecayedStateTable,
    TeamDecayedStateTable,
    TeamMatchupDecayedStateTable,
)
from dota_oracle_common.utils.set_logging import get_logger

from datetime import datetime


logger = get_logger(__name__)


class BaseHistoryRepositoryTest:
    """Base helpers for decayed-state repository tests."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Database Operation Helpers
    async def _get_player_hero_records(
        self, account_id: int, hero_id: int, match_id: Optional[int] = None
    ) -> List[PlayerHeroDecayedStateTable]:
        """Retrieve player-hero decayed state records."""

        stmt = select(PlayerHeroDecayedStateTable).where(
            PlayerHeroDecayedStateTable.account_id == account_id, PlayerHeroDecayedStateTable.hero_id == hero_id
        )
        if match_id is not None:
            stmt = stmt.where(PlayerHeroDecayedStateTable.match_id == match_id)

        result = await self.session.execute(stmt.execution_options(populate_existing=True))
        records = result.scalars().all()

        return list(records)

    async def _get_team_state_records(
        self, team_name: str, match_id: Optional[int] = None
    ) -> List[TeamDecayedStateTable]:
        """Retrieve team decayed state records."""

        stmt = select(TeamDecayedStateTable).where(TeamDecayedStateTable.team_name == team_name)
        if match_id is not None:
            stmt = stmt.where(TeamDecayedStateTable.match_id == match_id)

        result = await self.session.execute(stmt.execution_options(populate_existing=True))
        records = result.scalars().all()

        return list(records)

    async def _get_team_matchup_records(
        self, team1_name: str, team2_name: str, match_id: Optional[int] = None
    ) -> List[TeamMatchupDecayedStateTable]:
        """Retrieve team matchup decayed state records."""
        stmt = select(TeamMatchupDecayedStateTable).where(
            TeamMatchupDecayedStateTable.team1_name == team1_name,
            TeamMatchupDecayedStateTable.team2_name == team2_name,
        )
        if match_id is not None:
            stmt = stmt.where(TeamMatchupDecayedStateTable.match_id == match_id)

        result = await self.session.execute(stmt.execution_options(populate_existing=True))
        records = result.scalars().all()

        return list(records)

    async def _get_hero_records(self, hero_id: int, match_id: Optional[int] = None) -> List[HeroDecayedStateTable]:
        """Retrieve hero decayed state records."""

        stmt = select(HeroDecayedStateTable).where(HeroDecayedStateTable.hero_id == hero_id)
        if match_id is not None:
            stmt = stmt.where(HeroDecayedStateTable.match_id == match_id)

        result = await self.session.execute(stmt.execution_options(populate_existing=True))
        records = result.scalars().all()

        return list(records)

    async def _count_records_in_table(self, table_class: Any) -> int:
        """Count total records in a history table."""
        stmt = select(table_class)
        result = await self.session.execute(stmt.execution_options(populate_existing=True))
        return len(result.scalars().all())

    # Assertion Helpers
    def _assert_record_count_equals(self, expected_count: int, actual_records: List[Any], context: str = ""):
        """Assert that record count matches expected."""
        actual_count = len(actual_records)
        assert actual_count == expected_count, (
            f"{context} - Record count mismatch: " f"expected {expected_count}, got {actual_count}"
        )

    def _assert_player_hero_state_equals(
        self,
        record: PlayerHeroDecayedStateTable,
        expected_account_id: int,
        expected_hero_id: int,
        expected_match_id: int,
        expected_decayed_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
        context: str = "",
    ):
        """Assert player-hero decayed state values."""
        assert (
            record.account_id == expected_account_id
        ), f"{context} - account_id mismatch: expected {expected_account_id}, got {record.account_id}"
        assert (
            record.hero_id == expected_hero_id
        ), f"{context} - hero_id mismatch: expected {expected_hero_id}, got {record.hero_id}"
        assert (
            record.match_id == expected_match_id
        ), f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        assert (
            record.decayed_wins == expected_decayed_wins
        ), f"{context} - decayed_wins mismatch: expected {expected_decayed_wins}, got {record.decayed_wins}"
        assert (
            record.decayed_games == expected_decayed_games
        ), f"{context} - decayed_games mismatch: expected {expected_decayed_games}, got {record.decayed_games}"
        assert (
            record.last_update_time == expected_last_update_time
        ), f"{context} - last_update_time mismatch: expected {expected_last_update_time}, got {record.last_update_time}"

    def _assert_team_state_equals(
        self,
        record: TeamDecayedStateTable,
        expected_team_id: int,
        expected_team_name: str,
        expected_match_id: int,
        expected_decayed_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
        context: str = "",
    ):
        """Assert team decayed state values."""
        assert (
            record.team_id == expected_team_id
        ), f"{context} - team_id mismatch: expected {expected_team_id}, got {record.team_id}"
        assert (
            record.team_name == expected_team_name
        ), f"{context} - team_name mismatch: expected {expected_team_name}, got {record.team_name}"
        assert (
            record.match_id == expected_match_id
        ), f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        assert (
            record.decayed_wins == expected_decayed_wins
        ), f"{context} - decayed_wins mismatch: expected {expected_decayed_wins}, got {record.decayed_wins}"
        assert (
            record.decayed_games == expected_decayed_games
        ), f"{context} - decayed_games mismatch: expected {expected_decayed_games}, got {record.decayed_games}"
        assert (
            record.last_update_time == expected_last_update_time
        ), f"{context} - last_update_time mismatch: expected {expected_last_update_time}, got {record.last_update_time}"

    def _assert_team_matchup_state_equals(
        self,
        record: TeamMatchupDecayedStateTable,
        expected_team1_id: int,
        expected_team2_id: int,
        expected_team1_name: str,
        expected_team2_name: str,
        expected_match_id: int,
        expected_decayed_t1_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
        context: str = "",
    ):
        """Assert team matchup decayed state values."""
        assert (
            record.team1_id == expected_team1_id
        ), f"{context} - team1_id mismatch: expected {expected_team1_id}, got {record.team1_id}"
        assert (
            record.team2_id == expected_team2_id
        ), f"{context} - team2_id mismatch: expected {expected_team2_id}, got {record.team2_id}"
        assert (
            record.team1_name == expected_team1_name
        ), f"{context} - team1_name mismatch: expected {expected_team1_name}, got {record.team1_name}"
        assert (
            record.team2_name == expected_team2_name
        ), f"{context} - team2_name mismatch: expected {expected_team2_name}, got {record.team2_name}"
        assert (
            record.match_id == expected_match_id
        ), f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        assert (
            record.decayed_t1_wins == expected_decayed_t1_wins
        ), f"{context} - decayed_t1_wins mismatch: expected {expected_decayed_t1_wins}, got {record.decayed_t1_wins}"
        assert (
            record.decayed_games == expected_decayed_games
        ), f"{context} - decayed_games mismatch: expected {expected_decayed_games}, got {record.decayed_games}"
        assert (
            record.last_update_time == expected_last_update_time
        ), f"{context} - last_update_time mismatch: expected {expected_last_update_time}, got {record.last_update_time}"

    def _assert_hero_state_equals(
        self,
        record: HeroDecayedStateTable,
        expected_hero_id: int,
        expected_match_id: int,
        expected_decayed_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
        context: str = "",
    ):
        """Assert hero decayed state values."""
        assert (
            record.hero_id == expected_hero_id
        ), f"{context} - hero_id mismatch: expected {expected_hero_id}, got {record.hero_id}"
        assert (
            record.match_id == expected_match_id
        ), f"{context} - match_id mismatch: expected {expected_match_id}, got {record.match_id}"
        assert (
            record.decayed_wins == expected_decayed_wins
        ), f"{context} - decayed_wins mismatch: expected {expected_decayed_wins}, got {record.decayed_wins}"
        assert (
            record.decayed_games == expected_decayed_games
        ), f"{context} - decayed_games mismatch: expected {expected_decayed_games}, got {record.decayed_games}"
        assert (
            record.last_update_time == expected_last_update_time
        ), f"{context} - last_update_time mismatch: expected {expected_last_update_time}, got {record.last_update_time}"
