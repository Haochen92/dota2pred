import pytest
from unittest.mock import AsyncMock

from dota_oracle_common.repositories.history_repository import HistoryRepository


from live_orchestrator_app.services.history_update_service import HistoryUpdateService

F_PATH = "live_orchestrator_app.services.history_update_service"


@pytest.mark.asyncio
async def test_update_all_histories_for_match(
    mock_db_session_factory, mock_async_session, mocker, match_table_factory, match_outcome_table_factory
) -> None:

    # ARRANGE

    # Mock repo
    mock_history_repo = AsyncMock(spec=HistoryRepository)
    # Ensure getters return None so service computes from empty prior state
    mock_history_repo.get_team_state_before_by_id.return_value = None
    mock_history_repo.get_team_matchup_state_before_by_id.return_value = None
    mock_history_repo.get_player_hero_state_before.return_value = None
    mock_history_repo.get_hero_state_before.return_value = None

    # Mock instances
    match_details = match_table_factory.build(match_id=1001)
    setattr(match_details, "outcome", match_outcome_table_factory.build(match_id=1001))

    # Create test_subject
    service = HistoryUpdateService()

    # Mock methods
    get_match_details = mocker.patch.object(service, "_get_completed_match_details", return_value=match_details)

    # Mock repo creation
    mocker.patch(f"{F_PATH}.HistoryRepository", return_value=mock_history_repo)

    # ACT
    await service.update_all_histories_for_match(mock_db_session_factory, 1001)

    # ASSERT
    get_match_details.assert_awaited_once_with(1001, mock_async_session)

    # Verify repository methods were called (decayed state upserts)
    assert mock_history_repo.get_team_state_before_by_id.await_count == 2
    assert mock_history_repo.get_team_matchup_state_before_by_id.await_count == 1
    assert mock_history_repo.get_player_hero_state_before.await_count == 10
    assert mock_history_repo.get_hero_state_before.await_count == 10

    assert mock_history_repo.upsert_team_decayed_states.await_count == 1
    assert mock_history_repo.upsert_team_matchup_decayed_states.await_count == 1
    assert mock_history_repo.upsert_player_hero_decayed_states.await_count == 1
    assert mock_history_repo.upsert_hero_decayed_states.await_count == 1
