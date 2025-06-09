import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from dota_oracle.data_repository.history_repository import HistoryRepository
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.utils import get_logger, TaskRunner

from dota_oracle.models.match import MatchTable, MatchOutcomeTable
from dota_oracle.models.utils import AsyncTask

from dota_oracle.live_pipeline.services.history_update_service import HistoryUpdateService
from ...factories.repository_factories import MatchTableFactory, MatchOutcomeTableFactory

F_PATH = "dota_oracle.live_pipeline.services.history_update_service"

@pytest.mark.asyncio
async def test_update_histories(mock_async_session, mocker):
    
    # ARRANGE
    
    # Mock repo
    mock_history_repo = AsyncMock(spec=HistoryRepository)
    
    # Mock instances
    match_details = MatchTableFactory.build(match_id=1001)
    setattr(match_details, 'outcome', MatchOutcomeTableFactory.build(match_id=1001))
    match_outcome = match_details.outcome
    
    # Create test_subject
    service = HistoryUpdateService()
    
    # Mock methods
    get_match_details = mocker.patch.object(service, '_get_completed_match_details', return_value=match_details)
    update_team_history = mocker.patch.object(service, '_update_team_histories')
    update_player_hero_history = mocker.patch.object(service, '_update_player_hero_histories')

    # Mock repo creation
    mocker.patch(f"{F_PATH}.HistoryRepository", return_value=mock_history_repo)
    
    # ACT
    await service.update_histories(mock_async_session, 1001)
    
    # ASSERT
    get_match_details.assert_awaited_once()
    
    update_team_history.assert_awaited_once_with(
        mock_history_repo,
        match_details,
        match_outcome
    )
    
    update_player_hero_history.assert_awaited_once_with(
        mock_history_repo,
        match_details,
        match_outcome
    )
    
    