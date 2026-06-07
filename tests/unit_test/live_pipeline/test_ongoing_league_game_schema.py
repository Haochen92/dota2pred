"""Validation tests for the OngoingLeagueGame draft schema."""

import pytest
from pydantic import ValidationError

from dota_oracle_common.models.live_games.schema import (
    OngoingFaction,
    OngoingLeagueGame,
    OngoingPlayer,
    ScoreBoard,
    TeamData,
)


def _faction(hero_ids: list[int]) -> OngoingFaction:
    return OngoingFaction(
        players=[
            OngoingPlayer(player_slot=slot, account_id=1000 + slot, hero_id=hero) for slot, hero in enumerate(hero_ids)
        ]
    )


def _build_game(radiant_heroes: list[int], dire_heroes: list[int]) -> OngoingLeagueGame:
    return OngoingLeagueGame(
        match_id=123,
        league_id=1,
        radiant_team=TeamData(team_id=1),
        dire_team=TeamData(team_id=2),
        scoreboard=ScoreBoard(duration=0.0, radiant=_faction(radiant_heroes), dire=_faction(dire_heroes)),
    )


def test_valid_draft_with_ten_distinct_heroes_is_accepted() -> None:
    game = _build_game([1, 2, 3, 4, 5], [6, 7, 8, 9, 10])
    assert game.match_id == 123


def test_same_hero_on_both_teams_is_rejected() -> None:
    # Mirrors the production crash: hero 14 on radiant and dire.
    with pytest.raises(ValidationError, match="Duplicate hero_ids"):
        _build_game([14, 2, 3, 4, 5], [6, 7, 8, 9, 14])


def test_duplicate_hero_on_one_team_is_rejected() -> None:
    with pytest.raises(ValidationError, match="Duplicate hero_ids"):
        _build_game([35, 35, 35, 35, 5], [6, 7, 8, 9, 10])
