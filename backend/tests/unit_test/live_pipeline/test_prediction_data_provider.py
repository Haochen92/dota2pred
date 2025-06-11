import pytest
from unittest.mock import AsyncMock

from ...factories.unit_test_factory import PredictionWorkItemFactory
from ...factories.redis_models_factory import StreamMatchEventDataFactory


@pytest.mark.asyncio
async def test_get_work_items_successfully(prediction_data_provider, mocker):
    # Create mock events
    mock_events = {
        "event_1": StreamMatchEventDataFactory.build(match_id=12345),
        "event_2": StreamMatchEventDataFactory.build(match_id=67890),
        "event_3": StreamMatchEventDataFactory.build(match_id=54321)
    }
    
    mock_fetch_matches = mocker.patch.object(
        prediction_data_provider.redis,
        'fetch_matches_pending_prediction',
        return_value=mock_events
    )
    
    # ACT
    actual_work_items = await prediction_data_provider.get_work_items()
    
    # ASSERT
    assert len(actual_work_items) == 3
    assert all(item.match_id > 0 for item in actual_work_items)
    assert all(item.event_id in mock_events.keys() for item in actual_work_items)
    
    mock_fetch_matches.assert_awaited_once_with('consumer_one')


@pytest.mark.asyncio
async def test_get_work_items_no_events(prediction_data_provider, mocker):
    mock_fetch_matches = mocker.patch.object(
        prediction_data_provider.redis,
        'fetch_matches_pending_prediction',
        return_value={}
    )
    
    # ACT
    actual_work_items = await prediction_data_provider.get_work_items()
    
    # ASSERT
    assert len(actual_work_items) == 0
    mock_fetch_matches.assert_awaited_once_with('consumer_one')


@pytest.mark.asyncio
async def test_get_work_items_with_custom_consumer(prediction_data_provider, mocker):
    custom_consumer = "custom_consumer"
    mock_events = {
        "event_1": StreamMatchEventDataFactory.build(match_id=12345)
    }
    
    mock_fetch_matches = mocker.patch.object(
        prediction_data_provider.redis,
        'fetch_matches_pending_prediction',
        return_value=mock_events
    )
    
    # ACT
    actual_work_items = await prediction_data_provider.get_work_items(custom_consumer)
    
    # ASSERT
    assert len(actual_work_items) == 1
    mock_fetch_matches.assert_awaited_once_with(custom_consumer)


@pytest.mark.asyncio
async def test_get_work_items_filters_invalid_events(prediction_data_provider, mocker):
    # Create mix of valid and invalid events
    mock_events = {
        "valid_event": StreamMatchEventDataFactory.build(match_id=12345),
        "invalid_event_1": StreamMatchEventDataFactory.build(match_id=0),  # Invalid: match_id = 0
        "invalid_event_2": StreamMatchEventDataFactory.build(match_id=-1),  # Invalid: negative match_id
    }
    
    mock_fetch_matches = mocker.patch.object(
        prediction_data_provider.redis,
        'fetch_matches_pending_prediction',
        return_value=mock_events
    )
    
    # ACT
    actual_work_items = await prediction_data_provider.get_work_items()
    
    # ASSERT
    assert len(actual_work_items) == 1  # Only valid event should be included
    assert actual_work_items[0].match_id == 12345
    assert actual_work_items[0].event_id == "valid_event"


def test_is_event_data_valid_with_valid_data(prediction_data_provider):
    valid_event = StreamMatchEventDataFactory.build(match_id=12345)
    
    # ACT
    result = prediction_data_provider._is_event_data_valid(valid_event)
    
    # ASSERT
    assert result is True


def test_is_event_data_valid_with_none(prediction_data_provider):
    # ACT
    result = prediction_data_provider._is_event_data_valid(None)
    
    # ASSERT
    assert result is False


def test_is_event_data_valid_with_zero_match_id(prediction_data_provider):
    invalid_event = StreamMatchEventDataFactory.build(match_id=0)
    
    # ACT
    result = prediction_data_provider._is_event_data_valid(invalid_event)
    
    # ASSERT
    assert result is False


def test_is_event_data_valid_with_negative_match_id(prediction_data_provider):
    invalid_event = StreamMatchEventDataFactory.build(match_id=-1)
    
    # ACT
    result = prediction_data_provider._is_event_data_valid(invalid_event)
    
    # ASSERT
    assert result is False


def test_is_event_data_valid_with_non_integer_match_id(prediction_data_provider, mocker):
    # Create mock event with string match_id
    mock_event = mocker.Mock()
    mock_event.match_id = "invalid_id"
    
    # ACT
    result = prediction_data_provider._is_event_data_valid(mock_event)
    
    # ASSERT
    assert result is False


def test_is_event_data_valid_with_missing_match_id(prediction_data_provider, mocker):
    # Create mock event without match_id attribute
    mock_event = mocker.Mock()
    del mock_event.match_id
    
    # ACT
    result = prediction_data_provider._is_event_data_valid(mock_event)
    
    # ASSERT
    assert result is False