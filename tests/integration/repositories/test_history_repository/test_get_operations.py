"""
Tests for decayed-state history repository get operations.
"""

import pytest
from datetime import datetime, timedelta, timezone

from dota_oracle_common.repositories.history_repository import HistoryRepository

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_completed_match(
    db_session,
    match_table_factory,
    match_outcome_table_factory,
    *,
    match_id: int,
    start_time: datetime,
    with_decayed_state: bool = False,
    hero_decayed_state_table_factory=None,
) -> None:
    """Seed a completed match (details + outcome), optionally with its hero decayed-state rows."""
    db_session.add(match_table_factory.build(match_id=match_id, start_time=start_time))
    db_session.add(match_outcome_table_factory.build(match_id=match_id))
    if with_decayed_state:
        db_session.add(hero_decayed_state_table_factory.build(match_id=match_id, last_update_time=start_time))
    await db_session.flush()


class TestGetTeamStateBefore:
    @pytest.mark.parametrize(
        "test_scenario,team_name,before_time,expected_match_id,expected_decayed_wins,expected_decayed_games",
        [
            (
                "get_latest_team_state_before_cutoff",
                "team_secret",
                datetime(2023, 1, 5, tzinfo=timezone.utc),
                1004,
                1.6,
                3.1,
            ),
            (
                "get_team_state_with_earlier_cutoff",
                "team_secret",
                datetime(2023, 1, 3, tzinfo=timezone.utc),
                1002,
                1.0,
                1.8,
            ),
            (
                "get_nonexistent_team_returns_none",
                "team_spirit",
                datetime(2023, 1, 5, tzinfo=timezone.utc),
                None,
                None,
                None,
            ),
        ],
    )
    async def test_get_team_state_before(
        self,
        history_repository_test_subject: HistoryRepository,
        seed_history_data,
        test_scenario: str,
        team_name: str,
        before_time: datetime,
        expected_match_id: int | None,
        expected_decayed_wins: float | None,
        expected_decayed_games: float | None,
    ) -> None:
        result = await history_repository_test_subject.get_team_state_before(
            team_name=team_name, before_time=before_time
        )

        if expected_match_id is None:
            assert result is None, test_scenario
            return

        assert result is not None, test_scenario
        assert result.match_id == expected_match_id, test_scenario
        assert result.decayed_wins == expected_decayed_wins, test_scenario
        assert result.decayed_games == expected_decayed_games, test_scenario

    async def test_get_team_state_before_by_id(
        self, history_repository_test_subject: HistoryRepository, seed_history_data
    ) -> None:
        result = await history_repository_test_subject.get_team_state_before_by_id(
            team_id=1,
            before_time=datetime(2023, 1, 4, tzinfo=timezone.utc),
        )

        assert result is not None
        assert result.team_name == "team_secret"
        assert result.match_id == 1003


class TestGetTeamMatchupStateBefore:
    @pytest.mark.parametrize(
        "test_scenario,team_one,team_two,before_time,expected_match_id,expected_decayed_t1_wins,expected_decayed_games",
        [
            (
                "get_latest_matchup_state_before_cutoff",
                "team_secret",
                "PSG_LGD",
                datetime(2023, 1, 5, tzinfo=timezone.utc),
                1004,
                0.7,
                3.0,
            ),
            (
                "matchup_name_order_is_normalized",
                "PSG_LGD",
                "team_secret",
                datetime(2023, 1, 4, tzinfo=timezone.utc),
                1003,
                0.7,
                2.4,
            ),
            (
                "nonexistent_matchup_returns_none",
                "team_secret",
                "team_spirit",
                datetime(2023, 1, 5, tzinfo=timezone.utc),
                None,
                None,
                None,
            ),
        ],
    )
    async def test_get_team_matchup_state_before(
        self,
        history_repository_test_subject: HistoryRepository,
        seed_history_data,
        test_scenario: str,
        team_one: str,
        team_two: str,
        before_time: datetime,
        expected_match_id: int | None,
        expected_decayed_t1_wins: float | None,
        expected_decayed_games: float | None,
    ) -> None:
        result = await history_repository_test_subject.get_team_matchup_state_before(
            team_one=team_one,
            team_two=team_two,
            before_time=before_time,
        )

        if expected_match_id is None:
            assert result is None, test_scenario
            return

        assert result is not None, test_scenario
        assert result.match_id == expected_match_id, test_scenario
        assert result.decayed_t1_wins == expected_decayed_t1_wins, test_scenario
        assert result.decayed_games == expected_decayed_games, test_scenario

    async def test_get_team_matchup_state_before_by_id(
        self,
        history_repository_test_subject: HistoryRepository,
        seed_history_data,
    ) -> None:
        by_forward_order = await history_repository_test_subject.get_team_matchup_state_before_by_id(
            team1_id=1,
            team2_id=2,
            before_time=datetime(2023, 1, 4, tzinfo=timezone.utc),
        )
        by_reverse_order = await history_repository_test_subject.get_team_matchup_state_before_by_id(
            team1_id=2,
            team2_id=1,
            before_time=datetime(2023, 1, 4, tzinfo=timezone.utc),
        )

        assert by_forward_order is not None
        assert by_reverse_order is not None
        assert by_forward_order.match_id == 1003
        assert by_reverse_order.match_id == 1003


class TestGetPlayerHeroStateBefore:
    @pytest.mark.parametrize(
        "test_scenario,account_id,hero_id,before_time,expected_match_id,expected_decayed_wins,expected_decayed_games",
        [
            (
                "get_latest_player_hero_state_before_cutoff",
                1,
                10,
                datetime(2023, 1, 5, tzinfo=timezone.utc),
                1004,
                2.4,
                3.7,
            ),
            (
                "get_player_hero_state_with_earlier_cutoff",
                1,
                10,
                datetime(2023, 1, 3, tzinfo=timezone.utc),
                1002,
                1.8,
                2.1,
            ),
            (
                "get_nonexistent_player_hero_returns_none",
                99,
                10,
                datetime(2023, 1, 5, tzinfo=timezone.utc),
                None,
                None,
                None,
            ),
        ],
    )
    async def test_get_player_hero_state_before(
        self,
        history_repository_test_subject: HistoryRepository,
        seed_history_data,
        test_scenario: str,
        account_id: int,
        hero_id: int,
        before_time: datetime,
        expected_match_id: int | None,
        expected_decayed_wins: float | None,
        expected_decayed_games: float | None,
    ) -> None:
        result = await history_repository_test_subject.get_player_hero_state_before(
            account_id=account_id,
            hero_id=hero_id,
            before_time=before_time,
        )

        if expected_match_id is None:
            assert result is None, test_scenario
            return

        assert result is not None, test_scenario
        assert result.match_id == expected_match_id, test_scenario
        assert result.decayed_wins == expected_decayed_wins, test_scenario
        assert result.decayed_games == expected_decayed_games, test_scenario


class TestGetHeroStateBefore:
    @pytest.mark.parametrize(
        "test_scenario,hero_id,before_time,expected_match_id,expected_decayed_wins,expected_decayed_games",
        [
            ("get_latest_hero_state_before_cutoff", 10, datetime(2023, 1, 4, tzinfo=timezone.utc), 1003, 1.4, 2.4),
            ("get_nonexistent_hero_returns_none", 999, datetime(2023, 1, 4, tzinfo=timezone.utc), None, None, None),
        ],
    )
    async def test_get_hero_state_before(
        self,
        history_repository_test_subject: HistoryRepository,
        seed_history_data,
        test_scenario: str,
        hero_id: int,
        before_time: datetime,
        expected_match_id: int | None,
        expected_decayed_wins: float | None,
        expected_decayed_games: float | None,
    ) -> None:
        result = await history_repository_test_subject.get_hero_state_before(hero_id=hero_id, before_time=before_time)

        if expected_match_id is None:
            assert result is None, test_scenario
            return

        assert result is not None, test_scenario
        assert result.match_id == expected_match_id, test_scenario
        assert result.decayed_wins == expected_decayed_wins, test_scenario
        assert result.decayed_games == expected_decayed_games, test_scenario


class TestGetOperationsEmptyDatabase:
    async def test_get_team_state_before_empty_database(
        self, history_repository_test_subject: HistoryRepository
    ) -> None:
        result = await history_repository_test_subject.get_team_state_before(
            team_name="team_secret",
            before_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        )
        assert result is None

    async def test_get_player_hero_state_before_empty_database(
        self,
        history_repository_test_subject: HistoryRepository,
    ) -> None:
        result = await history_repository_test_subject.get_player_hero_state_before(
            account_id=1,
            hero_id=10,
            before_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        )
        assert result is None

    async def test_get_team_matchup_state_before_empty_database(
        self,
        history_repository_test_subject: HistoryRepository,
    ) -> None:
        result = await history_repository_test_subject.get_team_matchup_state_before(
            team_one="team_secret",
            team_two="PSG_LGD",
            before_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        )
        assert result is None

    async def test_get_hero_state_before_empty_database(
        self, history_repository_test_subject: HistoryRepository
    ) -> None:
        result = await history_repository_test_subject.get_hero_state_before(
            hero_id=10,
            before_time=datetime(2023, 1, 2, tzinfo=timezone.utc),
        )
        assert result is None


class TestGetEarliestMissingDecayedStateTime:
    async def test_returns_earliest_completed_match_missing_states(
        self,
        history_repository_test_subject: HistoryRepository,
        db_session,
        match_table_factory,
        match_outcome_table_factory,
        hero_decayed_state_table_factory,
    ) -> None:
        now = datetime.now(timezone.utc)
        # Two matches missing states (3d and 1d ago) + one that already has states (2d ago).
        await _seed_completed_match(
            db_session,
            match_table_factory,
            match_outcome_table_factory,
            match_id=7001,
            start_time=now - timedelta(days=3),
        )
        await _seed_completed_match(
            db_session,
            match_table_factory,
            match_outcome_table_factory,
            match_id=7002,
            start_time=now - timedelta(days=1),
        )
        await _seed_completed_match(
            db_session,
            match_table_factory,
            match_outcome_table_factory,
            match_id=7003,
            start_time=now - timedelta(days=2),
            with_decayed_state=True,
            hero_decayed_state_table_factory=hero_decayed_state_table_factory,
        )

        result = await history_repository_test_subject.get_earliest_missing_decayed_state_time()

        assert result is not None
        # Earliest match missing states is 7001 (3 days ago), not the state-complete 7003.
        assert abs((result - (now - timedelta(days=3))).total_seconds()) < 5

    async def test_within_days_bound_ignores_old_gaps(
        self,
        history_repository_test_subject: HistoryRepository,
        db_session,
        match_table_factory,
        match_outcome_table_factory,
    ) -> None:
        now = datetime.now(timezone.utc)
        # Only an old (200d) match is missing states.
        await _seed_completed_match(
            db_session,
            match_table_factory,
            match_outcome_table_factory,
            match_id=7101,
            start_time=now - timedelta(days=200),
        )

        # Bounded search ignores it; unbounded search finds it.
        assert await history_repository_test_subject.get_earliest_missing_decayed_state_time(within_days=120) is None
        assert await history_repository_test_subject.get_earliest_missing_decayed_state_time() is not None

    async def test_returns_none_when_all_completed_matches_have_states(
        self,
        history_repository_test_subject: HistoryRepository,
        db_session,
        match_table_factory,
        match_outcome_table_factory,
        hero_decayed_state_table_factory,
    ) -> None:
        now = datetime.now(timezone.utc)
        await _seed_completed_match(
            db_session,
            match_table_factory,
            match_outcome_table_factory,
            match_id=7201,
            start_time=now - timedelta(days=1),
            with_decayed_state=True,
            hero_decayed_state_table_factory=hero_decayed_state_table_factory,
        )

        assert await history_repository_test_subject.get_earliest_missing_decayed_state_time() is None
