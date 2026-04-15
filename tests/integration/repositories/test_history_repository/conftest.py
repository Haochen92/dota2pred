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
    player_hero_decayed_state_table_factory,
    team_decayed_state_table_factory,
    team_matchup_decayed_state_table_factory,
    hero_decayed_state_table_factory,
):
    """Seeds decayed-state data for history repository tests."""

    logger.info("Seeding history data for read operations")

    player_hero_data = [
        player_hero_decayed_state_table_factory.build(
            account_id=1,
            hero_id=10,
            match_id=1001,
            decayed_wins=1.0,
            decayed_games=1.0,
            last_update_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
        player_hero_decayed_state_table_factory.build(
            account_id=1,
            hero_id=10,
            match_id=1002,
            decayed_wins=1.8,
            decayed_games=2.1,
            last_update_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        ),
        player_hero_decayed_state_table_factory.build(
            account_id=1,
            hero_id=10,
            match_id=1003,
            decayed_wins=2.4,
            decayed_games=3.0,
            last_update_time=datetime(2023, 1, 3, tzinfo=timezone.utc),
        ),
        player_hero_decayed_state_table_factory.build(
            account_id=1,
            hero_id=10,
            match_id=1004,
            decayed_wins=2.4,
            decayed_games=3.7,
            last_update_time=datetime(2023, 1, 4, tzinfo=timezone.utc),
        ),
        player_hero_decayed_state_table_factory.build(
            account_id=1,
            hero_id=10,
            match_id=1005,
            decayed_wins=2.4,
            decayed_games=4.2,
            last_update_time=datetime(2023, 1, 5, tzinfo=timezone.utc),
        ),
        player_hero_decayed_state_table_factory.build(
            account_id=2,
            hero_id=20,
            match_id=2001,
            decayed_wins=0.9,
            decayed_games=1.0,
            last_update_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    team_state_data = [
        team_decayed_state_table_factory.build(
            team_id=1,
            team_name="team_secret",
            match_id=1001,
            decayed_wins=1.0,
            decayed_games=1.0,
            last_update_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
        team_decayed_state_table_factory.build(
            team_id=1,
            team_name="team_secret",
            match_id=1002,
            decayed_wins=1.0,
            decayed_games=1.8,
            last_update_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        ),
        team_decayed_state_table_factory.build(
            team_id=1,
            team_name="team_secret",
            match_id=1003,
            decayed_wins=1.0,
            decayed_games=2.5,
            last_update_time=datetime(2023, 1, 3, tzinfo=timezone.utc),
        ),
        team_decayed_state_table_factory.build(
            team_id=1,
            team_name="team_secret",
            match_id=1004,
            decayed_wins=1.6,
            decayed_games=3.1,
            last_update_time=datetime(2023, 1, 4, tzinfo=timezone.utc),
        ),
        team_decayed_state_table_factory.build(
            team_id=1,
            team_name="team_secret",
            match_id=1005,
            decayed_wins=2.2,
            decayed_games=3.8,
            last_update_time=datetime(2023, 1, 5, tzinfo=timezone.utc),
        ),
        team_decayed_state_table_factory.build(
            team_id=2,
            team_name="PSG_LGD",
            match_id=2001,
            decayed_wins=1.0,
            decayed_games=1.0,
            last_update_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    team_matchup_state_data = [
        team_matchup_decayed_state_table_factory.build(
            team1_id=1,
            team2_id=2,
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1001,
            decayed_t1_wins=0.0,
            decayed_games=1.0,
            last_update_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
        team_matchup_decayed_state_table_factory.build(
            team1_id=1,
            team2_id=2,
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1002,
            decayed_t1_wins=0.0,
            decayed_games=1.8,
            last_update_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        ),
        team_matchup_decayed_state_table_factory.build(
            team1_id=1,
            team2_id=2,
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1003,
            decayed_t1_wins=0.7,
            decayed_games=2.4,
            last_update_time=datetime(2023, 1, 3, tzinfo=timezone.utc),
        ),
        team_matchup_decayed_state_table_factory.build(
            team1_id=1,
            team2_id=2,
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1004,
            decayed_t1_wins=0.7,
            decayed_games=3.0,
            last_update_time=datetime(2023, 1, 4, tzinfo=timezone.utc),
        ),
        team_matchup_decayed_state_table_factory.build(
            team1_id=1,
            team2_id=2,
            team1_name="PSG_LGD",
            team2_name="team_secret",
            match_id=1005,
            decayed_t1_wins=1.2,
            decayed_games=3.5,
            last_update_time=datetime(2023, 1, 5, tzinfo=timezone.utc),
        ),
    ]

    hero_state_data = [
        hero_decayed_state_table_factory.build(
            hero_id=10,
            match_id=1001,
            decayed_wins=0.6,
            decayed_games=1.0,
            last_update_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
        hero_decayed_state_table_factory.build(
            hero_id=10,
            match_id=1002,
            decayed_wins=1.1,
            decayed_games=1.8,
            last_update_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        ),
        hero_decayed_state_table_factory.build(
            hero_id=10,
            match_id=1003,
            decayed_wins=1.4,
            decayed_games=2.4,
            last_update_time=datetime(2023, 1, 3, tzinfo=timezone.utc),
        ),
        hero_decayed_state_table_factory.build(
            hero_id=20,
            match_id=2001,
            decayed_wins=0.9,
            decayed_games=1.0,
            last_update_time=datetime(2023, 1, 1, tzinfo=timezone.utc),
        ),
    ]

    all_data = player_hero_data + team_state_data + team_matchup_state_data + hero_state_data
    db_session.add_all(all_data)

    await db_session.flush()
    logger.info("History seeding complete.")

    yield
