import pytest
from unittest.mock import MagicMock
from dota_oracle_common.models.pipeline import FeatureEngineeringWorkItem


F_PATH = "live_orchestrator_app.feature_engineering.feature_engineering_data_provider"


@pytest.mark.asyncio
async def test_get_work_items_successfully(
    feature_engineering_data_provider, mocker, stream_match_event_data_factory, match_table_factory
) -> None:
    """
    Tests the happy path where events are fetched, validated, and matched with DB details.
    This version includes stronger assertions on the output.
    """
    # ARRANGE
    stream_event_data_1 = stream_match_event_data_factory.build()
    stream_event_data_2 = stream_match_event_data_factory.build()
    mock_events_dict = {"event_1": stream_event_data_1, "event_2": stream_event_data_2}

    match_id_1 = stream_event_data_1.match_id
    match_id_2 = stream_event_data_2.match_id
    mock_data_lookup = {
        match_id_1: match_table_factory.build(match_id=match_id_1),
        match_id_2: match_table_factory.build(match_id=match_id_2),
    }

    # Mock external and internal calls
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.return_value = mock_events_dict
    mocker.patch.object(feature_engineering_data_provider, "_validate_events", return_value=mock_events_dict)
    mocker.patch.object(feature_engineering_data_provider, "_fetch_match_details", return_value=mock_data_lookup)

    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items()

    # ASSERT
    assert len(actual_work_items) == 2

    # Stronger Assertions: Check the content of the work items
    work_item_1 = next(item for item in actual_work_items if item.event_id == "event_1")
    work_item_2 = next(item for item in actual_work_items if item.event_id == "event_2")

    assert isinstance(work_item_1, FeatureEngineeringWorkItem)
    assert work_item_1.event_data == stream_event_data_1
    assert work_item_1.match_details == mock_data_lookup[match_id_1]

    assert isinstance(work_item_2, FeatureEngineeringWorkItem)
    assert work_item_2.event_data == stream_event_data_2
    assert work_item_2.match_details == mock_data_lookup[match_id_2]

    # Assert interactions
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.assert_awaited_once()
    feature_engineering_data_provider._validate_events.assert_called_once_with(mock_events_dict)
    feature_engineering_data_provider._fetch_match_details.assert_awaited_once_with(mock_events_dict)


@pytest.mark.asyncio
async def test_get_work_items_when_redis_returns_no_events(feature_engineering_data_provider):
    """Tests that the function exits early and returns an empty list if Redis has no new events."""
    # ARRANGE
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.return_value = {}

    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items()

    # ASSERT
    assert actual_work_items == []
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_work_items_when_all_events_are_invalid(
    feature_engineering_data_provider, mocker, stream_match_event_data_factory
):
    """Tests that an empty list is returned if all fetched events fail validation."""
    # ARRANGE
    mock_events_dict = {"event_1": stream_match_event_data_factory.build()}
    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.return_value = mock_events_dict

    # Mock validation to return no valid events
    mock_validate = mocker.patch.object(feature_engineering_data_provider, "_validate_events", return_value={})
    mock_fetch = mocker.patch.object(feature_engineering_data_provider, "_fetch_match_details")

    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items()

    # ASSERT
    assert actual_work_items == []
    mock_validate.assert_called_once_with(mock_events_dict)
    mock_fetch.assert_not_called()


@pytest.mark.asyncio
async def test_get_work_items_with_partially_missing_match_details(
    feature_engineering_data_provider, mocker, stream_match_event_data_factory, match_table_factory
):
    """Tests that only work items for which match details were found are returned."""
    # ARRANGE
    event_data_found = stream_match_event_data_factory.build()
    event_data_missing = stream_match_event_data_factory.build()
    mock_events_dict = {"event_found": event_data_found, "event_missing": event_data_missing}

    # DB lookup only contains details for the first event
    mock_data_lookup = {event_data_found.match_id: match_table_factory.build(match_id=event_data_found.match_id)}

    feature_engineering_data_provider.redis.fetch_new_matches_for_feature_eng.return_value = mock_events_dict
    mocker.patch.object(feature_engineering_data_provider, "_validate_events", return_value=mock_events_dict)
    mocker.patch.object(feature_engineering_data_provider, "_fetch_match_details", return_value=mock_data_lookup)

    # ACT
    actual_work_items = await feature_engineering_data_provider.get_work_items()

    # ASSERT
    assert len(actual_work_items) == 1
    assert actual_work_items[0].event_id == "event_found"
    assert actual_work_items[0].match_details.match_id == event_data_found.match_id


@pytest.mark.parametrize(
    "event_data, is_valid",
    [
        ("valid_event", True),
        (None, False),
        (MagicMock(match_id=None), False),
        (MagicMock(match_id=0), False),
        (MagicMock(match_id=-123), False),
        (MagicMock(match_id="not-an-int"), False),
    ],
)
def test_is_event_data_valid(
    feature_engineering_data_provider,
    stream_match_event_data_factory,  # Fixture is still needed here
    event_data,
    is_valid,
):
    """Tests the validation logic for individual events with various inputs."""

    # If our parameter is the marker string, create a valid object from the factory
    if event_data == "valid_event":
        event_data = stream_match_event_data_factory.build(match_id=12345)

    # ACT & ASSERT
    assert feature_engineering_data_provider._is_event_data_valid(event_data) is is_valid


@pytest.mark.asyncio
async def test_fetch_match_details_successfully(
    feature_engineering_data_provider,
    mock_match_repository,
    mocker,
    stream_match_event_data_factory,
    match_table_factory,
):
    """Tests successful fetching and mapping of match details from the database."""
    # ARRANGE
    stream_event_data_1 = stream_match_event_data_factory.build()
    stream_event_data_2 = stream_match_event_data_factory.build()
    # Add a duplicate match_id to test that it's handled correctly
    stream_event_data_3 = stream_match_event_data_factory.build(match_id=stream_event_data_1.match_id)
    mock_events_dict = {"e1": stream_event_data_1, "e2": stream_event_data_2, "e3": stream_event_data_3}

    match_details_1 = match_table_factory.build(match_id=stream_event_data_1.match_id)
    match_details_2 = match_table_factory.build(match_id=stream_event_data_2.match_id)
    mock_match_details_list = [match_details_1, match_details_2]

    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)
    mock_match_repository.get_match_details.return_value = mock_match_details_list

    # ACT
    match_data_lookup = await feature_engineering_data_provider._fetch_match_details(mock_events_dict)

    # ASSERT
    assert len(match_data_lookup) == 2
    assert match_data_lookup[stream_event_data_1.match_id] == match_details_1
    assert match_data_lookup[stream_event_data_2.match_id] == match_details_2

    # Verify it was called once with a list of unique IDs
    expected_unique_ids = [stream_event_data_1.match_id, stream_event_data_2.match_id]
    mock_match_repository.get_match_details.assert_awaited_once()
    call_args = mock_match_repository.get_match_details.call_args.kwargs["input_id_list"]
    assert sorted(call_args) == sorted(expected_unique_ids)


@pytest.mark.asyncio
async def test_fetch_match_details_handles_db_exception(
    feature_engineering_data_provider, mock_match_repository, mocker, stream_match_event_data_factory
):
    """Tests that a database exception is caught and an empty dict is returned."""
    # ARRANGE
    mock_events_dict = {"e1": stream_match_event_data_factory.build()}
    mocker.patch(f"{F_PATH}.MatchRepository", return_value=mock_match_repository)

    # Make the repository call raise an error
    mock_match_repository.get_match_details.side_effect = Exception("Database connection failed")

    # ACT
    match_data_lookup = await feature_engineering_data_provider._fetch_match_details(mock_events_dict)

    # ASSERT
    # The method should gracefully handle the error and return empty
    assert match_data_lookup == {}
