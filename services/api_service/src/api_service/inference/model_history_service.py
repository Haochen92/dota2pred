from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.metrics import roc_auc_score, brier_score_loss

from dota_oracle_common.models.api.schema import (
    ModelHistoryRequest,
    ModelHistoryResponse,
    ModelPerformanceEntry,
    CalibrationPlot,
    ConfidenceBin,
    AggregateBy,
)
from dota_oracle_common.models.match import MatchTable, MatchOutcomeTable
from dota_oracle_common.models.inference import MatchPredictionTable
from dota_oracle_common.utils.set_logging import get_logger

from dota_oracle_common.utils.time_utils import to_utc_datetime_object

CALIBRATION_BINS = [0.5, 0.6, 0.7, 0.8, 1.0]
CALIBRATION_LABELS = ["50-60%", "60-70%", "70-80%", ">80%"]

logger = get_logger(__name__)


class ModelHistoryService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def get_model_performance_history(self, request: ModelHistoryRequest) -> ModelHistoryResponse:
        """
        Parse ModelHistoryRequest to fetch match predictions and outcomes from the database,
        filter by the requested history range

        Compute time-series performance metrics
        (Accuracy, AUC, root Brier) aggregated by the specified period.

        Also computes a calibration plot for the entire filtered dataset.

        """

        date_range_value = request.history_range.value

        end_date = datetime.now(tz=timezone.utc)
        start_date = (
            end_date - timedelta(days=date_range_value)
            if date_range_value > 0
            else datetime(2000, 1, 1, tzinfo=timezone.utc)
        )

        # 1) Fetch raw, columns needed for calculations from the DB
        stmt = (
            select(
                MatchTable.start_time.label("start_time"),
                MatchOutcomeTable.radiant_win.label("actual_win"),
                MatchPredictionTable.prediction.label("prediction"),
                MatchPredictionTable.prediction_probability.label("probability"),
                MatchPredictionTable.prediction_date.label("prediction_date"),
                MatchPredictionTable.match_id.label("match_id"),
                MatchPredictionTable.predictor_name.label("predictor_name"),
            )
            .select_from(MatchTable)
            .join(MatchPredictionTable, MatchPredictionTable.match_id == MatchTable.match_id)
            .join(MatchOutcomeTable, MatchOutcomeTable.match_id == MatchTable.match_id)
            .where(
                and_(
                    MatchTable.start_time >= start_date,
                    MatchTable.start_time < end_date,
                    MatchOutcomeTable.radiant_win.is_not(None),
                    MatchPredictionTable.prediction.is_not(None),
                    MatchPredictionTable.prediction_probability.is_not(None),
                )
            )
        )

        res = await self.session.execute(stmt)
        rows = res.mappings().all()
        if not rows:
            logger.info(f"No match prediction data found for the specified history range: {request.history_range}")
            return ModelHistoryResponse(history=[], calibration_plot=CalibrationPlot(bins=[]))

        df = self._build_validated_prediction_df(rows)  # type: ignore

        if df is None or df.empty:
            logger.info("No valid match prediction data after validation.")
            return ModelHistoryResponse(history=[], calibration_plot=CalibrationPlot(bins=[]))

        df_for_metrics = df[["start_time", "actual_win", "prediction", "probability"]]

        history = self._calculate_time_series_metrics(df_for_metrics, request.aggregate_by)
        calibration_plot = self._calculate_calibration_plot(df_for_metrics[["actual_win", "probability"]])

        return ModelHistoryResponse(history=history, calibration_plot=calibration_plot)

    def _build_validated_prediction_df(self, rows: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
        """
        Converts raw database rows into a clean, validated DataFrame for performance analysis.

        This involves:
        - Handling empty input.
        - Enforcing correct data types (bool, numeric, datetime).
        - Handling missing 'prediction' values by deriving from 'probability'.
        - Dropping rows with invalid 'probability' after coercion.
        - Ensuring the latest prediction per match/predictor is used.
        """
        if not rows:
            return None

        df = pd.DataFrame(rows)

        # Ensure expected dtypes and handle potential missing values
        df["actual_win"] = df["actual_win"].astype(bool)

        # Fallback for 'prediction' if it's missing (defensive programming)
        if "prediction" not in df or df["prediction"].isna().any():
            df["prediction"] = df["probability"] >= 0.5
        else:
            df["prediction"] = df["prediction"].astype(bool)

        # Coerce probability to numeric and drop rows where it's invalid
        df["probability"] = pd.to_numeric(df["probability"], errors="coerce")
        df = df.dropna(subset=["probability"])

        if df.empty:
            return None

        df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
        df["prediction_date"] = pd.to_datetime(df["prediction_date"], utc=True)

        # Keep only the latest prediction per match and predictor, in case there are multiple models in future versions
        df = df.sort_values("prediction_date").drop_duplicates(["match_id", "predictor_name"], keep="last").copy()

        logger.info(f"Validated prediction DataFrame constructed with {len(df)} entries.")

        return df

    def _calculate_calibration_plot(self, df: pd.DataFrame) -> CalibrationPlot:
        """
        Calculates and return symmetric calibration plot data from the given DataFrame.

        Confidence level is symmetrized around 0.5. For predicted_probabilty of >= 0.5, confidence = predicted_probability,
        else confidence = 1 - predicted_probability.

        The DataFrame is grouped by the constructed confidence bins, and for each bin, the following metrics are calculated:
           - match_count: number of matches in the bin
           - bin_accuracy: proportion of correct predictions in the bin
           - average_confidence: average confidence level of matches in the bin

        Returns a CalibrationPlot object containing a list of ConfidenceBin objects for each bin: bin_name, match_count, bin_accuracy, average_confidence.

        Required Columns: 'actual_win' (bool), 'probability' (float).
        """
        if df.empty:
            return CalibrationPlot(bins=[])

        # --- CONSTRUCTIONS OF PLOT COLUMNS

        # Construct confidence column with symmetrized confidence levels
        conf_col_arr = np.where(df["probability"] >= 0.5, df["probability"], 1.0 - df["probability"])

        # Construct correctness column
        pred_win = df["probability"] >= 0.5
        correct_col = pred_win == df["actual_win"]

        # Use pandas cut to create bins from continuous confidence levels into discrete bins as defined by CALIBRATION_BINS, labelled with CALIBRATION_LABELS
        # Right inclusive bin (0.5, 0.6], left_inclusive for the first bin (lowest_value)
        binned_conf_col = pd.cut(
            conf_col_arr, bins=CALIBRATION_BINS, labels=CALIBRATION_LABELS, right=True, include_lowest=True
        )

        intermediate_df = pd.DataFrame(
            {"bin": binned_conf_col, "conf": conf_col_arr, "correct": correct_col.astype(float)}
        )

        aggregated_df = (
            intermediate_df.groupby("bin", observed=True)  # first only group by bin for categories with values
            .agg(
                # Use agg method to create 3 aggregated cols: match_count, bin_accuracy, average_confidence
                match_count=("conf", "count"),
                bin_accuracy=("correct", "mean"),
                average_confidence=("conf", "mean"),
            )
            .reindex(CALIBRATION_LABELS)  # reindex to ensure all bins present in final output
        )
        aggregated_df = aggregated_df.fillna({"match_count": 0, "bin_accuracy": np.nan, "average_confidence": np.nan})

        confidence_bins: List[ConfidenceBin] = []

        for bin_name, row in aggregated_df.iterrows():
            confidence_bins.append(
                ConfidenceBin(
                    bin_name=str(bin_name),
                    match_count=int(row.match_count),
                    bin_accuracy=float(row.bin_accuracy) if not pd.isna(row.bin_accuracy) else None,
                    average_confidence=float(row.average_confidence) if not pd.isna(row.average_confidence) else None,
                )
            )

        logger.info(f"Calibration plot calculated with {len(confidence_bins)} bins.")

        return CalibrationPlot(bins=confidence_bins)

    def _calculate_time_series_metrics(
        self, df: pd.DataFrame, aggregate_by: AggregateBy
    ) -> List[ModelPerformanceEntry]:
        """Calculates time-series metrics (Accuracy, AUC, root Brier) grouped by time.

        Expects columns: 'start_time' (datetime), 'actual_win' (bool), 'prediction' (bool), 'probability' (float).
        """
        if df.empty:
            return []

        # Create time_delta frequency string for Pandas Grouper, (number + unit ('D')) from AggregateBy enum value
        freq = f"{aggregate_by.value}D"

        df_indexed = df.set_index("start_time")
        # Turn continuous time into discrete periods by grouping with the given frequency
        grouped = df_indexed.groupby(pd.Grouper(freq=freq))

        history: List[ModelPerformanceEntry] = []

        for period_date, group in grouped:
            if group.empty:
                continue

            y_true = group["actual_win"].astype(int)
            y_pred_class = group["prediction"].astype(int)
            y_pred_prob = group["probability"].astype(float)

            # Calculate metrics
            accuracy = float(np.mean(y_true == y_pred_class))
            auc = (
                float(roc_auc_score(y_true, y_pred_prob)) if group["actual_win"].nunique() > 1 else 0.5
            )  # AUC only valid if both classes present
            root_brier = float(np.sqrt(brier_score_loss(y_true, y_pred_prob)))

            # Ensure timezone-aware datetime
            period_dt = to_utc_datetime_object(period_date)

            history.append(
                ModelPerformanceEntry(
                    date=period_dt,
                    accuracy=accuracy,
                    auc=auc,
                    root_brier=root_brier,
                )
            )

            logger.info(
                f"Calculated metrics for period starting {period_dt}: Accuracy={accuracy}, AUC={auc}, root Brier={root_brier}"
            )
        return history
