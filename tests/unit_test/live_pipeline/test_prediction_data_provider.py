import pytest
from dota_oracle_common.models.redis.schema import ConsumedEvent, PredictionPayload


@pytest.mark.asyncio
async def test_get_work_items_successfully(prediction_data_provider, prediction_payload_factory, mocker) -> None:
    # Create mock events
    payload_1 = prediction_payload_factory.build(match_id=12345)
    payload_2 = prediction_payload_factory.build(match_id=67890)
    payload_3 = prediction_payload_factory.build(match_id=54321)

    mock_events = [
        ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_1", payload=payload_1),
        ConsumedEvent[PredictionPayload](match_id=67890, event_id="event_2", payload=payload_2),
        ConsumedEvent[PredictionPayload](match_id=54321, event_id="event_3", payload=payload_3),
    ]

    mock_fetch_matches = mocker.patch.object(
        prediction_data_provider.redis, "fetch_matches_for_prediction", return_value=mock_events
    )

    # ACT
    actual_work_items = await prediction_data_provider.get_work_items()

    # ASSERT
    assert len(actual_work_items) == 3
    assert all(item.match_id > 0 for item in actual_work_items)
    assert all(item.event_id in ["event_1", "event_2", "event_3"] for item in actual_work_items)

    mock_fetch_matches.assert_awaited_once_with("consumer_one")


@pytest.mark.asyncio
async def test_get_work_items_no_events(prediction_data_provider, mocker) -> None:
    mock_fetch_matches = mocker.patch.object(
        prediction_data_provider.redis, "fetch_matches_for_prediction", return_value=[]
    )

    # ACT
    actual_work_items = await prediction_data_provider.get_work_items()

    # ASSERT
    assert len(actual_work_items) == 0
    mock_fetch_matches.assert_awaited_once_with("consumer_one")


@pytest.mark.asyncio
async def test_get_work_items_with_custom_consumer(
    prediction_data_provider, prediction_payload_factory, mocker
) -> None:
    custom_consumer = "custom_consumer"
    payload = prediction_payload_factory.build(match_id=12345)
    mock_events = [ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_1", payload=payload)]

    mock_fetch_matches = mocker.patch.object(
        prediction_data_provider.redis, "fetch_matches_for_prediction", return_value=mock_events
    )

    # ACT
    actual_work_items = await prediction_data_provider.get_work_items(custom_consumer)

    # ASSERT
    assert len(actual_work_items) == 1
    mock_fetch_matches.assert_awaited_once_with(custom_consumer)
