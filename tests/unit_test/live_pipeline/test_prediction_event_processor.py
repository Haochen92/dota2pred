import pytest
import numpy as np
from unittest.mock import AsyncMock

F_PATH = "live_orchestrator_app.prediction.prediction_event_processor"


@pytest.mark.asyncio
async def test_process_event_successfully(
    prediction_event_processor, prediction_work_item_factory, mock_async_session, mocker
) -> None:
    work_item = prediction_work_item_factory.build()
    mock_input_array = np.array([[1, 2, 3, 4, 5]])

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        return_value=mock_input_array,
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store"
    )

    # ACT
    await prediction_event_processor.process_event(work_item)

    # ASSERT
    mock_prepare_features.assert_awaited_once_with(work_item.match_id, mock_async_session)
    mock_predict_and_store.assert_awaited_once_with(
        db_session=mock_async_session, match_id=work_item.match_id, input_array_for_inference=mock_input_array
    )


@pytest.mark.asyncio
async def test_process_event_feature_preparation_returns_none(
    prediction_event_processor, prediction_work_item_factory, mock_async_session, mocker
) -> None:
    work_item = prediction_work_item_factory.build()

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service, "prepare_features_for_inference", return_value=None
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store"
    )

    # ACT & ASSERT
    with pytest.raises(
        ValueError, match=f"Feature preparation failed or returned empty features for match {work_item.match_id}"
    ):
        await prediction_event_processor.process_event(work_item)

    mock_prepare_features.assert_awaited_once_with(work_item.match_id, mock_async_session)
    mock_predict_and_store.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_feature_preparation_returns_empty_array(
    prediction_event_processor, prediction_work_item_factory, mock_async_session, mocker
) -> None:
    work_item = prediction_work_item_factory.build()
    empty_array = np.array([])

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        return_value=empty_array,
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store"
    )

    # ACT & ASSERT
    with pytest.raises(
        ValueError, match=f"Feature preparation failed or returned empty features for match {work_item.match_id}"
    ):
        await prediction_event_processor.process_event(work_item)

    mock_prepare_features.assert_awaited_once_with(work_item.match_id, mock_async_session)
    mock_predict_and_store.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_feature_preparation_service_raises_exception(
    prediction_event_processor, prediction_work_item_factory, mock_async_session, mocker
) -> None:
    work_item = prediction_work_item_factory.build()
    feature_error = Exception("Feature preparation failed")

    mock_prepare_features = mocker.patch.object(
        prediction_event_processor.feature_preparation_service,
        "prepare_features_for_inference",
        side_effect=feature_error,
    )

    mock_predict_and_store = mocker.patch.object(
        prediction_event_processor.match_prediction_service, "predict_and_store"
    )

    # ACT & ASSERT
    with pytest.raises(Exception, match="Feature preparation failed"):
        await prediction_event_processor.process_event(work_item)

    mock_prepare_features.assert_awaited_once_with(work_item.match_id, mock_async_session)
    mock_predict_and_store.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_event_prediction_service_raises_exception(
    prediction_event_processor, prediction_work_item_factory, mock_async_session, mocker
) -> None:
    work_item = prediction_work_item_factory.build()
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

    # ACT & ASSERT
    with pytest.raises(Exception, match="Prediction failed"):
        await prediction_event_processor.process_event(work_item)

    mock_prepare_features.assert_awaited_once_with(work_item.match_id, mock_async_session)
    mock_predict_and_store.assert_awaited_once_with(
        db_session=mock_async_session, match_id=work_item.match_id, input_array_for_inference=mock_input_array
    )


@pytest.mark.asyncio
async def test_process_event_session_transaction_handling(
    prediction_event_processor, prediction_work_item_factory, mock_async_session, mocker
) -> None:
    work_item = prediction_work_item_factory.build()
    mock_input_array = np.array([[1, 2, 3, 4, 5]])

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

    mocker.patch.object(prediction_event_processor.match_prediction_service, "predict_and_store")

    # ACT
    await prediction_event_processor.process_event(work_item)

    # ASSERT
    # The db_session_factory should be called once to create the session
    prediction_event_processor.db_session_factory.assert_called_once()
    mock_async_session.begin.assert_called_once()
    mock_transaction_context.__aenter__.assert_awaited_once()
    mock_transaction_context.__aexit__.assert_awaited_once()
