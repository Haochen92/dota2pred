import pytest
from unittest.mock import AsyncMock

from dota_oracle_common.repositories.history_repository import HistoryRepository


from live_orchestrator_app.services.history_update_service import HistoryUpdateService

F_PATH = "live_orchestrator_app.services.history_update_service"


@pytest.mark.asyncio
async def test_update_histories(
    mock_db_session_factory, mock_async_session, mocker, match_table_factory, match_outcome_table_factory
) -> None:

    # ARRANGE

    # Mock repo
    mock_history_repo = AsyncMock(spec=HistoryRepository)

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
    await service.update_histories(mock_db_session_factory, 1001)

    # ASSERT
    get_match_details.assert_awaited_once_with(1001, mock_async_session)

    # Verify repository methods were called (the actual history updates)
    assert mock_history_repo.add_team_match_outcome.await_count == 2
    assert mock_history_repo.add_team_matchup_outcome.await_count == 1
    assert mock_history_repo.add_player_hero_match_outcome.await_count == 10
