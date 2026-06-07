import pytest
from datetime import datetime, timezone
from types import SimpleNamespace

from dota_oracle_common.models.features import PlayerHeroFeatureTable

FUNCTION_FP = "dota_oracle_pipeline.feature_engineering.player_hero_features_creator"


@pytest.mark.asyncio
async def test_create_player_hero_features_success(
    player_hero_features_creator,
    mock_async_session,
    match_table_factory,
    mocker,
) -> None:
    match_instance = match_table_factory.build(match_id=1001)

    mock_calculate_hero_prior = mocker.patch.object(
        player_hero_features_creator, "_calculate_hero_prior", return_value=0.55
    )
    mock_calculate_decayed = mocker.patch.object(
        player_hero_features_creator,
        "_calculate_decayed_win_rate",
        return_value=0.6,
    )

    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_async_session,
        match_instances=[match_instance],
    )

    assert len(result) == 1
    feature_row = result[0]
    assert isinstance(feature_row, PlayerHeroFeatureTable)
    assert feature_row.match_id == 1001
    assert feature_row.player_hero_0_win_rate == 0.6
    assert feature_row.player_hero_128_win_rate == 0.6
    assert mock_calculate_hero_prior.await_count == 10
    assert mock_calculate_decayed.await_count == 10


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "missing_data",
    [
        pytest.param({"match_id": 124, "slot_0_hero_id": None}, id="missing_hero_id"),
        pytest.param({"match_id": 125, "start_time": None}, id="missing_start_time"),
    ],
)
async def test_create_features_skips_match_with_missing_structural_data(
    player_hero_features_creator,
    mock_async_session,
    match_table_factory,
    mocker,
    missing_data: dict,
) -> None:
    """hero_id / start_time are structural -- without them no prior can be computed, so the
    whole match is skipped. (A missing account_id is handled separately via the prior fallback.)"""
    match_instance = match_table_factory.build(**missing_data)
    mock_logger_error = mocker.patch(f"{FUNCTION_FP}.logger.error")

    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_async_session,
        match_instances=[match_instance],
    )

    assert result == []
    mock_logger_error.assert_called_once()


@pytest.mark.asyncio
async def test_anonymous_account_falls_back_to_hero_prior(
    player_hero_features_creator,
    mock_async_session,
    match_table_factory,
    mocker,
) -> None:
    """A missing (anonymous) account_id must NOT drop the match: that slot falls back to the
    hero prior, and the match still produces a full feature row."""
    # slot 0 anonymous; all other slots keep their account_ids from the factory.
    match_instance = match_table_factory.build(match_id=1002, slot_0_account_id=None)

    mocker.patch.object(player_hero_features_creator, "_calculate_hero_prior", return_value=0.55)
    mock_decayed = mocker.patch.object(player_hero_features_creator, "_calculate_decayed_win_rate", return_value=0.6)

    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_async_session,
        match_instances=[match_instance],
    )

    assert len(result) == 1
    feature_row = result[0]
    # Anonymous slot 0 uses the hero prior; the other 9 slots use the decayed per-player rate.
    assert feature_row.player_hero_0_win_rate == 0.55
    assert feature_row.player_hero_1_win_rate == 0.6
    # Decayed rate computed only for the 9 non-anonymous slots (slot 0 skipped it).
    assert mock_decayed.await_count == 9


@pytest.mark.asyncio
async def test_create_features_skips_match_when_decayed_rate_calculation_fails(
    player_hero_features_creator,
    mock_async_session,
    match_table_factory,
    mocker,
) -> None:
    match_instance = match_table_factory.build(match_id=789)
    mocker.patch.object(player_hero_features_creator, "_calculate_hero_prior", return_value=0.5)
    mocker.patch.object(
        player_hero_features_creator,
        "_calculate_decayed_win_rate",
        side_effect=Exception("decayed-rate-failed"),
    )

    result = await player_hero_features_creator.create_player_hero_features(
        session=mock_async_session,
        match_instances=[match_instance],
    )
    assert result == []


@pytest.mark.asyncio
async def test_calculate_decayed_win_rate_uses_hero_prior_when_no_history(
    player_hero_features_creator,
    mock_async_session,
    mocker,
) -> None:
    mock_repo_instance = mocker.AsyncMock()
    mock_repo_instance.get_player_hero_state_before.return_value = None
    mocker.patch(f"{FUNCTION_FP}.HistoryRepository", return_value=mock_repo_instance)

    win_rate = await player_hero_features_creator._calculate_decayed_win_rate(
        session=mock_async_session,
        account_id=1,
        hero_id=2,
        hero_prior=0.42,
        before=datetime.now(timezone.utc),
    )

    assert win_rate == pytest.approx(0.42)
    mock_repo_instance.get_player_hero_state_before.assert_awaited_once()


@pytest.mark.asyncio
async def test_calculate_decayed_win_rate_applies_decay_and_prior(
    player_hero_features_creator,
    mock_async_session,
    mocker,
) -> None:
    before = datetime(2025, 1, 10, tzinfo=timezone.utc)
    state = SimpleNamespace(
        decayed_wins=4.0,
        decayed_games=10.0,
        last_update_time=datetime(2025, 1, 5, tzinfo=timezone.utc),
    )
    mock_repo_instance = mocker.AsyncMock()
    mock_repo_instance.get_player_hero_state_before.return_value = state
    mocker.patch(f"{FUNCTION_FP}.HistoryRepository", return_value=mock_repo_instance)
    mock_decay = mocker.patch(f"{FUNCTION_FP}.apply_decay_to_pair", return_value=(2.0, 5.0))

    hero_prior = 0.3
    win_rate = await player_hero_features_creator._calculate_decayed_win_rate(
        session=mock_async_session,
        account_id=1,
        hero_id=2,
        hero_prior=hero_prior,
        before=before,
    )

    expected = (2.0 + player_hero_features_creator.player_prior_count * hero_prior) / (
        5.0 + player_hero_features_creator.player_prior_count
    )
    assert win_rate == pytest.approx(expected)
    mock_decay.assert_called_once()


@pytest.mark.asyncio
async def test_calculate_hero_prior_uses_default_when_no_history(
    player_hero_features_creator,
    mock_async_session,
    mocker,
) -> None:
    mock_repo_instance = mocker.AsyncMock()
    mock_repo_instance.get_hero_state_before.return_value = None
    mocker.patch(f"{FUNCTION_FP}.HistoryRepository", return_value=mock_repo_instance)

    hero_prior = await player_hero_features_creator._calculate_hero_prior(
        session=mock_async_session,
        hero_id=2,
        before=datetime.now(timezone.utc),
    )

    assert hero_prior == pytest.approx(player_hero_features_creator.hero_prior_mean)


@pytest.mark.asyncio
async def test_calculate_hero_prior_applies_decay_and_bayesian_smoothing(
    player_hero_features_creator,
    mock_async_session,
    mocker,
) -> None:
    before = datetime(2025, 1, 10, tzinfo=timezone.utc)
    state = SimpleNamespace(
        decayed_wins=8.0,
        decayed_games=16.0,
        last_update_time=datetime(2025, 1, 5, tzinfo=timezone.utc),
    )
    mock_repo_instance = mocker.AsyncMock()
    mock_repo_instance.get_hero_state_before.return_value = state
    mocker.patch(f"{FUNCTION_FP}.HistoryRepository", return_value=mock_repo_instance)
    mock_decay = mocker.patch(f"{FUNCTION_FP}.apply_decay_to_pair", return_value=(3.0, 6.0))

    hero_prior = await player_hero_features_creator._calculate_hero_prior(
        session=mock_async_session,
        hero_id=2,
        before=before,
    )

    expected = (3.0 + player_hero_features_creator.hero_prior_count * player_hero_features_creator.hero_prior_mean) / (
        6.0 + player_hero_features_creator.hero_prior_count
    )
    assert hero_prior == pytest.approx(expected)
    mock_decay.assert_called_once()
