import pytest
from dota_oracle_common.models.redis.schema import ConsumedEvent, FeatureEngineeringPayload


F_PATH = "live_orchestrator_app.feature_engineering.feature_engineering_data_provider"


@pytest.mark.asyncio
async def test_get_work_items_successfully(feature_engineering_data_provider, mocker, match_table_factory) -> None:
    """
    Tests the happy path where events are fetched from Redis.
    """
    # ARRANGE
    match_id_1 = 12345
    match_id_2 = 67890

    match_details_1 = match_table_factory.build(match_id=match_id_1)
    match_details_2 = match_table_factory.build(match_id=match_id_2)

    consumed_event_1 = ConsumedEvent[FeatureEngineeringPayload](
        match_id=match_id_1, event_id="event_1", payload=FeatureEngineeringPayload(match_details=match_details_1)
    )
    consumed_event_2 = ConsumedEvent[FeatureEngineeringPayload](
        match_id=match_id_2, event_id="event_2", payload=FeatureEngineeringPayload(match_details=match_details_2)
    )
    mock_events_list = [consumed_event_1, consumed_event_2]

    # Mock external calls
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.return_value = mock_events_list

    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items()

    # ASSERT
    assert len(actual_work_items) == 2

    # Check the content of the work items
    work_item_1 = next(item for item in actual_work_items if item.event_id == "event_1")
    work_item_2 = next(item for item in actual_work_items if item.event_id == "event_2")

    assert isinstance(work_item_1, ConsumedEvent)
    assert work_item_1.match_id == match_id_1
    assert work_item_1.payload.match_details == match_details_1

    assert isinstance(work_item_2, ConsumedEvent)
    assert work_item_2.match_id == match_id_2
    assert work_item_2.payload.match_details == match_details_2

    # Assert interactions
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_work_items_when_redis_returns_no_events(feature_engineering_data_provider):
    """Tests that the function returns an empty list if Redis has no new events."""
    # ARRANGE
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.return_value = []

    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items()

    # ASSERT
    assert actual_work_items == []
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_work_items_with_custom_consumer(feature_engineering_data_provider, match_table_factory):
    """Tests that custom consumer name is passed through to redis service."""
    # ARRANGE
    custom_consumer = "custom_consumer"
    match_details = match_table_factory.build()

    consumed_event = ConsumedEvent[FeatureEngineeringPayload](
        match_id=12345, event_id="event_1", payload=FeatureEngineeringPayload(match_details=match_details)
    )

    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.return_value = [consumed_event]

    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items(custom_consumer)

    # ASSERT
    assert len(actual_work_items) == 1
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.assert_awaited_once_with(custom_consumer)
