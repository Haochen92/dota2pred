"""
Shared fixtures and base classes for history repository tests.
"""

import pytest
import pytest_asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from dota_oracle_common.utils.set_logging import get_logger


logger = get_logger(__name__)

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest_asyncio.fixture(scope="function")
async def seed_history_data(
    db_session: AsyncSession,
    player_hero_history_table_factory,
    team_history_table_factory,
    team_matchup_history_table_factory,
):
    """Seeds data for history repository read operations tests."""

    logger.info("Seeding history data for read operations")

    player_hero_data = [
        player_hero_history_table_factory.build(
            account_id=1, hero_id=10, win=True, match_id=1001, start_time=datetime(2023, 1, 1, tzinfo=timezone.utc)
        ),
        player_hero_history_table_factory.build(
            account_id=1, hero_id=10, win=True, match_id=1002, start_time=datetime(2023, 1, 2, tzinfo=timezone.utc)
        ),
        player_hero_history_table_factory.build(
            account_id=1, hero_id=10, win=True, match_id=1003, start_time=datetime(2023, 1, 3, tzinfo=timezone.utc)
        ),
        player_hero_history_table_factory.build(
            account_id=1, hero_id=10, win=False, match_id=1004, start_time=datetime(2023, 1, 4, tzinfo=timezone.utc)
        ),
        player_hero_history_table_factory.build(
            account_id=1, hero_id=10, win=False, match_id=1005, start_time=datetime(2023, 1, 5, tzinfo=timezone.utc)
        ),
        player_hero_history_table_factory.build(
            account_id=2, hero_id=20, win=True, match_id=2001, start_time=datetime(2023, 1, 1, tzinfo=timezone.utc)
        ),
    ]

    team_history_data = [
        team_history_table_factory.build(
            team_name="team_secret", match_id=1001, win=True, start_time=datetime(2023, 1, 1, tzinfo=timezone.utc)
        ),
        team_history_table_factory.build(
            team_name="team_secret", match_id=1002, win=False, start_time=datetime(2023, 1, 2, tzinfo=timezone.utc)
        ),
        team_history_table_factory.build(
            team_name="team_secret", match_id=1003, win=False, start_time=datetime(2023, 1, 3, tzinfo=timezone.utc)
        ),
        team_history_table_factory.build(
            team_name="team_secret", match_id=1004, win=True, start_time=datetime(2023, 1, 4, tzinfo=timezone.utc)
        ),
        team_history_table_factory.build(
            team_name="team_secret", match_id=1005, win=True, start_time=datetime(2023, 1, 5, tzinfo=timezone.utc)
        ),
        team_history_table_factory.build(
            team_name="PSG_LGD", match_id=2001, win=True, start_time=datetime(2023, 1, 1, tzinfo=timezone.utc)
        ),
    ]

    team_match_up_data = [
        team_matchup_history_table_factory.build(
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1001,
            win=False,
            start_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
        team_matchup_history_table_factory.build(
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1002,
            win=False,
            start_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        ),
        team_matchup_history_table_factory.build(
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1003,
            win=True,
            start_time=datetime(2023, 1, 3, tzinfo=timezone.utc),
        ),
        team_matchup_history_table_factory.build(
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1004,
            win=False,
            start_time=datetime(2023, 1, 4, tzinfo=timezone.utc),
        ),
        team_matchup_history_table_factory.build(
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1005,
            win=True,
            start_time=datetime(2023, 1, 5, tzinfo=timezone.utc),
        ),
    ]

    all_data = player_hero_data + team_history_data + team_match_up_data
    db_session.add_all(all_data)

    await db_session.flush()
    logger.info("History seeding complete.")

    yield
