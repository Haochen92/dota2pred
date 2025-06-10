import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, ANY
from sqlalchemy.ext.asyncio import AsyncEngine


from dota_oracle.live_pipeline.services.history_update_service import HistoryUpdateService
from dota_oracle.data_repository.match_repository import MatchRepository
from dota_oracle.models.match import MatchOutcomeTable
from dota_oracle.models.pipeline import CompletionWorkItem
from dota_oracle.live_pipeline.completion.completion_event_processor import CompletionEventProcessor

from ...factories.unit_test_factory import CompletionWorkItemFactory

F_PATH = "dota_oracle.live_pipeline.completion.completion_event_processor"

@pytest_asyncio.fixture
async def completion_event_processor():
    mock_history_update_service = AsyncMock(spec=HistoryUpdateService)
    mock_db_engine = AsyncMock(spec=AsyncEngine)
    processor = CompletionEventProcessor(
        db_engine=mock_db_engine,
        history_update_service=mock_history_update_service
    )
    
    return processor


@pytest.mark.asyncio
async def test_process_events_successfully(
    mocker, 
    mock_async_session,
    completion_event_processor: CompletionEventProcessor):
    # ARRANGE
    mock_work_item = CompletionWorkItemFactory.build()
    mock_repository = AsyncMock(spec=MatchRepository)
    
    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_repository)
    
    mocked_async_session_class = mocker.patch(f"{F_PATH}.AsyncSession")
    mocked_async_session_class.return_value.__aenter__.return_value = mock_async_session
    mocked_async_session_class.return_value.__aexit__.return_value = None
    
    mock_update_outcome = mocker.patch.object(
        completion_event_processor,
        '_update_match_outcome'
    )
    mock_update_history = mocker.patch.object(
        completion_event_processor.history_updater,
        'update_histories'
    )
    
    
    # ACT
    await completion_event_processor.process_events(mock_work_item)
    
    # ASSERT
    mock_update_outcome.assert_awaited_once_with(
        match_repository=mock_repository,
        match_id=mock_work_item.event_data.match_id,
        match_outcome=mock_work_item.outcome
    )
    
    mock_update_history.assert_awaited_once_with(
        mock_async_session,
        mock_work_item.event_data.match_id
    )
    