import pytest
import numpy as np
from unittest.mock import AsyncMock
from dota_oracle_common.models.redis.schema import ConsumedEvent, PredictionPayload, CompletionPayload

F_PATH = "live_orchestrator_app.prediction.prediction_event_processor"


@pytest.mark.asyncio
async def test_process_event_successfully(
    prediction_event_processor, prediction_payload_factory, mock_async_session, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    payload = prediction_payload_factory.build()
    event = ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_123", payload=payload)

    mock_input_array = np.array([[1, 2, 3, 4, 5]])
    expected_prediction_result = True

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        return_value=mock_input_array,
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service,
        "predict_and_store",
        return_value=expected_prediction_result,
    )

    # Use the provided mock_db_session_factory
    prediction_event_processor.db_session_factory = mock_db_session_factory

    # Mock the transaction context
    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT
    result = await prediction_event_processor.process_event(event)

    # ASSERT
    assert isinstance(result, CompletionPayload)
    assert result.match_id == 12345
    assert result.radiant_win == expected_prediction_result

    mock_prepare_features.assert_awaited_once_with(payload, mock_async_session)
    mock_predict_and_store.assert_awaited_once_with(
        db_session=mock_async_session, match_id=12345, input_array_for_inference=mock_input_array
    )


@pytest.mark.asyncio
async def test_process_event_feature_preparation_returns_none(
    prediction_event_processor, prediction_payload_factory, mock_async_session, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    payload = prediction_payload_factory.build()
    event = ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_123", payload=payload)

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service, "prepare_features_for_inference", return_value=None
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store"
    )

    # Use the provided mock_db_session_factory
    prediction_event_processor.db_session_factory = mock_db_session_factory

    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT & ASSERT
    with pytest.raises(
        ValueError, match=f"Feature preparation failed or returned empty features for match {event.match_id}"
    ):
        await prediction_event_processor.process_event(event)

    mock_prepare_features.assert_awaited_once_with(payload, mock_async_session)
    mock_predict_and_store.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_feature_preparation_returns_empty_array(
    prediction_event_processor, prediction_payload_factory, mock_async_session, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    payload = prediction_payload_factory.build()
    event = ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_123", payload=payload)
    empty_array = np.array([])

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        return_value=empty_array,
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store"
    )

    # Use the provided mock_db_session_factory
    prediction_event_processor.db_session_factory = mock_db_session_factory

    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT & ASSERT
    with pytest.raises(
        ValueError, match=f"Feature preparation failed or returned empty features for match {event.match_id}"
    ):
        await prediction_event_processor.process_event(event)

    mock_prepare_features.assert_awaited_once_with(payload, mock_async_session)
    mock_predict_and_store.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_feature_preparation_service_raises_exception(
    prediction_event_processor, prediction_payload_factory, mock_async_session, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    payload = prediction_payload_factory.build()
    event = ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_123", payload=payload)
    feature_error = Exception("Feature preparation failed")

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        side_effect=feature_error,
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store"
    )

    # Use the provided mock_db_session_factory
    prediction_event_processor.db_session_factory = mock_db_session_factory

    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT & ASSERT
    with pytest.raises(Exception, match="Feature preparation failed"):
        await prediction_event_processor.process_event(event)

    mock_prepare_features.assert_awaited_once_with(payload, mock_async_session)
    mock_predict_and_store.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_prediction_service_raises_exception(
    prediction_event_processor, prediction_payload_factory, mock_async_session, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    payload = prediction_payload_factory.build()
    event = ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_123", payload=payload)
    mock_input_array = np.array([[1, 2, 3, 4, 5]])
    prediction_error = Exception("Prediction failed")

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        return_value=mock_input_array,
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store", side_effect=prediction_error
    )

    # Use the provided mock_db_session_factory
    prediction_event_processor.db_session_factory = mock_db_session_factory

    mock_transaction = AsyncMock()
    mock_async_session.begin.return_value = mock_transaction

    # ACT & ASSERT
    with pytest.raises(Exception, match="Prediction failed"):
        await prediction_event_processor.process_event(event)

    mock_prepare_features.assert_awaited_once_with(payload, mock_async_session)
    mock_predict_and_store.assert_awaited_once_with(
        db_session=mock_async_session, match_id=12345, input_array_for_inference=mock_input_array
    )


@pytest.mark.asyncio
async def test_process_event_session_transaction_handling(
    prediction_event_processor, prediction_payload_factory, mock_async_session, mock_db_session_factory, mocker
) -> None:
    # ARRANGE
    payload = prediction_payload_factory.build()
    event = ConsumedEvent[PredictionPayload](match_id=12345, event_id="event_123", payload=payload)
    mock_input_array = np.array([[1, 2, 3, 4, 5]])

    # Use the provided mock_db_session_factory
    prediction_event_processor.db_session_factory = mock_db_session_factory

    # Mock transaction context manager
    mock_transaction_context = AsyncMock()
    mock_transaction_context.__aenter__.return_value = None
    mock_transaction_context.__aexit__.return_value = None
    mock_async_session.begin.return_value = mock_transaction_context

    mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        return_value=mock_input_array,
    )

    mocker.patch.object(prediction_event_processor.match_prediction_service, "predict_and_store", return_value=True)

    # ACT
    await prediction_event_processor.process_event(event)

    # ASSERT
    # The db_session_factory should be called once to create the session
    mock_db_session_factory.assert_called_once()
    mock_async_session.begin.assert_called_once()
    mock_transaction_context.__aenter__.assert_awaited_once()
    mock_transaction_context.__aexit__.assert_awaited_once()
