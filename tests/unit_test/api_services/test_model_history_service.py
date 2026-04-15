"""
Unit tests for ModelHistoryService helper methods.
"""

import pandas as pd
import numpy as np
import pytest

from api_service.inference.model_history_service import ModelHistoryService
from dota_oracle_common.models.api.schema import AggregateBy, ModelHistoryRequest, ModelHistoryResponse


def _build_sample_df(n_days: int = 10) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_days, freq="D", tz="UTC")
    probs = np.linspace(0.4, 0.9, n_days)
    preds = probs >= 0.5
    actuals = np.array([i % 2 == 0 for i in range(n_days)])
    return pd.DataFrame(
        {
            "start_time": dates,
            "actual_win": actuals,
            "prediction": preds,
            "probability": probs,
        }
    )


def test_time_series_grouping_fixed_day_buckets(mock_async_session) -> None:
    svc = ModelHistoryService(db_session=mock_async_session)
    df = _build_sample_df(10)

    # Daily (1D) should yield 10 buckets
    daily = svc._calculate_time_series_metrics(df, AggregateBy.day)
    assert len(daily) == 10
    assert all(entry.date.tzinfo is not None for entry in daily)

    # Weekly (7D) should yield 2 buckets (1-7, 8-10)
    weekly = svc._calculate_time_series_metrics(df, AggregateBy.week)
    assert len(weekly) == 2

    # Monthly (30D) should yield 1 bucket for 10 days of data
    monthly = svc._calculate_time_series_metrics(df, AggregateBy.month)
    assert len(monthly) == 1


def test_calibration_plot_bins(mock_async_session) -> None:
    svc = ModelHistoryService(db_session=mock_async_session)
    df = _build_sample_df(10)
    plot = svc._calculate_calibration_plot(df[["actual_win", "probability"]])
    assert len(plot.bins) == 4
    # Total match_count across bins equals number of rows
    assert sum(b.match_count for b in plot.bins) == 10


@pytest.mark.asyncio
async def test_empty_result_returns_empty_response_with_calibration_plot_async(mocker) -> None:
    svc = ModelHistoryService(db_session=mocker.AsyncMock())

    class DummyResult:
        def mappings(self):
            return self

        def all(self):
            return []

    # Mock session.execute to return empty rows
    svc.session.execute = mocker.AsyncMock(return_value=DummyResult())

    req = ModelHistoryRequest(history_range=7, aggregate_by=AggregateBy.day)
    response = await svc.get_model_performance_history(req)

    assert isinstance(response, ModelHistoryResponse)
    assert response.history == []
    assert hasattr(response, "calibration_plot")
    assert response.calibration_plot.bins == []
