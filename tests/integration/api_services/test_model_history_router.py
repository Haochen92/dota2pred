"""
Integration-style tests for the Model History endpoint using the API layer client
with dependency-injected service mocks.
"""

from datetime import datetime, timezone

from dota_oracle_common.models.api.schema import (
    ModelHistoryResponse,
    ModelPerformanceEntry,
    CalibrationPlot,
)


def test_model_history_success(api_layer_client, mock_model_history_service):
    # Arrange: mock service return value
    entries = [
        ModelPerformanceEntry(
            date=datetime(2024, 1, 1, tzinfo=timezone.utc),
            accuracy=0.8,
            auc=0.75,
            root_brier=0.4,
        ),
        ModelPerformanceEntry(
            date=datetime(2024, 1, 2, tzinfo=timezone.utc),
            accuracy=0.7,
            auc=0.72,
            root_brier=0.45,
        ),
    ]
    mock_model_history_service.get_model_performance_history.return_value = ModelHistoryResponse(
        history=entries,
        calibration_plot=CalibrationPlot(bins=[]),
    )

    # Act
    resp = api_layer_client.get(
        "/inference/model_history",
        params={"history_range": 7, "aggregate_by": 1},
    )

    # Assert
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data
    assert "calibration_plot" in data
    assert isinstance(data["history"], list)
    assert len(data["history"]) == 2
    assert data["history"][0]["accuracy"] == 0.8
    assert data["history"][0]["auc"] == 0.75
    assert data["history"][0]["root_brier"] == 0.4


def test_model_history_validation_error(api_layer_client):
    # Missing required query params should return 422
    resp = api_layer_client.get("/inference/model_history")
    assert resp.status_code == 422
