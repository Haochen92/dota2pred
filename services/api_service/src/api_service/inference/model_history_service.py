from dota_oracle_common.models.api.schema import ModelHistoryRequest, ModelHistoryResponse, ModelPerformanceEntry
from dota_oracle_common.models.match import MatchTable, MatchOutcomeTable
from dota_oracle_common.models.inference import MatchPredictionTable
from datetime import datetime, timezone, timedelta
from sqlalchemy import func, select, case, Float, and_, true
from sqlalchemy.ext.asyncio import AsyncSession


class ModelHistoryService:
    def __init__(self, db_session: AsyncSession):
        self.session = db_session

    async def get_model_performance_history(self, request: ModelHistoryRequest) -> ModelHistoryResponse:
        """Process the model history request and return performance data."""

        date_range_value = request.history_range.value
        aggregate_by_unit = request.aggregate_by.name

        end_date = datetime.now(tz=timezone.utc)
        start_date = (
            end_date - timedelta(days=date_range_value)
            if date_range_value > 0
            else datetime.min.replace(tzinfo=timezone.utc)
        )

        period = func.date_trunc(aggregate_by_unit, MatchTable.start_time).label("period")

        epsilon = 1e-9  # Small constant to prevent division by zero

        accuracy_calc = func.avg(
            case((MatchPredictionTable.prediction == MatchOutcomeTable.radiant_win, 1.0), else_=0.0)  # type: ignore
        ).label("accuracy")

        true_positives = func.sum(
            case(
                (
                    and_(
                        MatchPredictionTable.prediction.is_(true()),  # type: ignore
                        MatchOutcomeTable.radiant_win.is_(true()),  # type: ignore
                    ),
                    1,
                ),
                else_=0,
            )
        ).cast(Float)

        total_predicted_positives = func.sum(
            case((MatchPredictionTable.prediction.is_(true()), 1), else_=0)  # type: ignore
        ).cast(Float)

        total_actual_positives = func.sum(
            case((MatchOutcomeTable.radiant_win.is_(true()), 1), else_=0)  # type: ignore
        ).cast(Float)

        statement = (
            select(
                period,
                accuracy_calc,
                (true_positives / (total_predicted_positives + epsilon)).label("precision"),
                (true_positives / (total_actual_positives + epsilon)).label("recall"),
            )
            .select_from(MatchTable)
            .join(MatchPredictionTable)
            .join(MatchOutcomeTable)
            .where(
                and_(
                    MatchTable.start_time >= start_date,  # type: ignore
                    MatchTable.start_time < end_date,  # type: ignore
                    MatchOutcomeTable.radiant_win.is_not(None),  # type: ignore
                    MatchPredictionTable.prediction.is_not(None),  # type: ignore
                )
            )
            .group_by(period)
            .order_by(period.asc())
        )

        result = await self.session.execute(statement)
        results = result.all()

        performance_history = [
            ModelPerformanceEntry(
                date=record.period,
                accuracy=record.accuracy or 0.0,
                precision=record.precision or 0.0,
                recall=record.recall or 0.0,
            )
            for record in results
        ]

        return ModelHistoryResponse(history=performance_history)
