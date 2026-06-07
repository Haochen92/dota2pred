"""
Tests for history repository upsert operations.
"""

import pytest
from datetime import datetime, timezone

from dota_oracle_common.models.histories import (
    HeroDecayedStateTable,
    PlayerHeroDecayedStateTable,
    TeamDecayedStateTable,
    TeamMatchupDecayedStateTable,
)
from dota_oracle_common.repositories.history_repository import HistoryRepository

from .base_history_repo import BaseHistoryRepositoryTest

pytestmark = pytest.mark.asyncio(loop_scope="session")


class TestUpsertPlayerHeroDecayedStates:
    @pytest.mark.parametrize(
        "test_scenario,record,expected_decayed_wins,expected_decayed_games,expected_last_update_time",
        [
            (
                "insert_new_player_hero_state",
                PlayerHeroDecayedStateTable(
                    account_id=3,
                    hero_id=10,
                    match_id=3001,
                    decayed_wins=0.4,
                    decayed_games=1.2,
                    last_update_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                0.4,
                1.2,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
            (
                "update_existing_player_hero_state",
                PlayerHeroDecayedStateTable(
                    account_id=1,
                    hero_id=10,
                    match_id=1001,
                    decayed_wins=9.0,
                    decayed_games=11.0,
                    last_update_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
                ),
                9.0,
                11.0,
                datetime(2025, 1, 2, tzinfo=timezone.utc),
            ),
        ],
    )
    async def test_upsert_player_hero_decayed_states(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
        test_scenario: str,
        record: PlayerHeroDecayedStateTable,
        expected_decayed_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
    ) -> None:
        await history_repository_test_subject.upsert_player_hero_decayed_states([record])

        records = await history_test_repository._get_player_hero_records(
            record.account_id, record.hero_id, record.match_id
        )
        history_test_repository._assert_record_count_equals(1, records, test_scenario)
        history_test_repository._assert_player_hero_state_equals(
            records[0],
            record.account_id,
            record.hero_id,
            record.match_id,
            expected_decayed_wins,
            expected_decayed_games,
            expected_last_update_time,
            test_scenario,
        )


class TestUpsertTeamDecayedStates:
    @pytest.mark.parametrize(
        "test_scenario,record,expected_decayed_wins,expected_decayed_games,expected_last_update_time",
        [
            (
                "insert_new_team_state",
                TeamDecayedStateTable(
                    team_id=3,
                    team_name="liquid",
                    match_id=3001,
                    decayed_wins=0.8,
                    decayed_games=1.0,
                    last_update_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                0.8,
                1.0,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
            (
                "update_existing_team_state",
                TeamDecayedStateTable(
                    team_id=1,
                    team_name="team_secret",
                    match_id=1001,
                    decayed_wins=5.5,
                    decayed_games=6.0,
                    last_update_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
                ),
                5.5,
                6.0,
                datetime(2025, 1, 2, tzinfo=timezone.utc),
            ),
        ],
    )
    async def test_upsert_team_decayed_states(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
        test_scenario: str,
        record: TeamDecayedStateTable,
        expected_decayed_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
    ) -> None:
        await history_repository_test_subject.upsert_team_decayed_states([record])

        records = await history_test_repository._get_team_state_records(record.team_name, record.match_id)
        history_test_repository._assert_record_count_equals(1, records, test_scenario)
        history_test_repository._assert_team_state_equals(
            records[0],
            record.team_id,
            record.team_name,
            record.match_id,
            expected_decayed_wins,
            expected_decayed_games,
            expected_last_update_time,
            test_scenario,
        )


class TestUpsertTeamMatchupDecayedStates:
    @pytest.mark.parametrize(
        "test_scenario,record,expected_team1_id,expected_team2_id,expected_decayed_t1_wins,expected_decayed_games,expected_last_update_time",
        [
            (
                "insert_new_team_matchup_state",
                TeamMatchupDecayedStateTable(
                    team1_id=3,
                    team2_id=4,
                    team1_name="liquid",
                    team2_name="navi",
                    match_id=3001,
                    decayed_t1_wins=0.7,
                    decayed_games=1.0,
                    last_update_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                3,
                4,
                0.7,
                1.0,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
            (
                "update_existing_team_matchup_state",
                TeamMatchupDecayedStateTable(
                    team1_id=1,
                    team2_id=2,
                    team1_name="PSG_LGD",
                    team2_name="team_secret",
                    match_id=1001,
                    decayed_t1_wins=4.0,
                    decayed_games=5.0,
                    last_update_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
                ),
                1,
                2,
                4.0,
                5.0,
                datetime(2025, 1, 2, tzinfo=timezone.utc),
            ),
        ],
    )
    async def test_upsert_team_matchup_decayed_states(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
        test_scenario: str,
        record: TeamMatchupDecayedStateTable,
        expected_team1_id: int,
        expected_team2_id: int,
        expected_decayed_t1_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
    ) -> None:
        await history_repository_test_subject.upsert_team_matchup_decayed_states([record])

        records = await history_test_repository._get_team_matchup_records(
            record.team1_name, record.team2_name, record.match_id
        )
        history_test_repository._assert_record_count_equals(1, records, test_scenario)
        history_test_repository._assert_team_matchup_state_equals(
            records[0],
            expected_team1_id,
            expected_team2_id,
            record.team1_name,
            record.team2_name,
            record.match_id,
            expected_decayed_t1_wins,
            expected_decayed_games,
            expected_last_update_time,
            test_scenario,
        )


class TestUpsertHeroDecayedStates:
    @pytest.mark.parametrize(
        "test_scenario,record,expected_decayed_wins,expected_decayed_games,expected_last_update_time",
        [
            (
                "insert_new_hero_state",
                HeroDecayedStateTable(
                    hero_id=35,
                    match_id=3001,
                    decayed_wins=0.3,
                    decayed_games=1.0,
                    last_update_time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                ),
                0.3,
                1.0,
                datetime(2025, 1, 1, tzinfo=timezone.utc),
            ),
            (
                "update_existing_hero_state",
                HeroDecayedStateTable(
                    hero_id=10,
                    match_id=1001,
                    decayed_wins=3.2,
                    decayed_games=4.1,
                    last_update_time=datetime(2025, 1, 2, tzinfo=timezone.utc),
                ),
                3.2,
                4.1,
                datetime(2025, 1, 2, tzinfo=timezone.utc),
            ),
        ],
    )
    async def test_upsert_hero_decayed_states(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
        test_scenario: str,
        record: HeroDecayedStateTable,
        expected_decayed_wins: float,
        expected_decayed_games: float,
        expected_last_update_time: datetime,
    ) -> None:
        await history_repository_test_subject.upsert_hero_decayed_states([record])

        records = await history_test_repository._get_hero_records(record.hero_id, record.match_id)
        history_test_repository._assert_record_count_equals(1, records, test_scenario)
        history_test_repository._assert_hero_state_equals(
            records[0],
            record.hero_id,
            record.match_id,
            expected_decayed_wins,
            expected_decayed_games,
            expected_last_update_time,
            test_scenario,
        )

    async def test_upsert_hero_decayed_states_dedupes_duplicate_keys_in_batch(
        self,
        history_repository_test_subject: HistoryRepository,
        history_test_repository: BaseHistoryRepositoryTest,
        seed_history_data,
    ) -> None:
        """A match where the same hero appears on both teams yields two rows with the same
        (hero_id, match_id) in one batch. Postgres would raise CardinalityViolationError on
        ON CONFLICT DO UPDATE; the repository must dedupe and keep the last occurrence."""
        last_update_time = datetime(2025, 1, 3, tzinfo=timezone.utc)
        duplicate_batch = [
            HeroDecayedStateTable(
                hero_id=35,
                match_id=4001,
                decayed_wins=1.0,
                decayed_games=2.0,
                last_update_time=last_update_time,
            ),
            HeroDecayedStateTable(
                hero_id=35,
                match_id=4001,
                decayed_wins=2.0,
                decayed_games=2.0,
                last_update_time=last_update_time,
            ),
        ]

        await history_repository_test_subject.upsert_hero_decayed_states(duplicate_batch)

        records = await history_test_repository._get_hero_records(35, 4001)
        history_test_repository._assert_record_count_equals(1, records, "dedupe_duplicate_keys_in_batch")
        history_test_repository._assert_hero_state_equals(
            records[0],
            35,
            4001,
            2.0,  # last occurrence wins
            2.0,
            last_update_time,
            "dedupe_duplicate_keys_in_batch",
        )
