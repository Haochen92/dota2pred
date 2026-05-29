# import logging
from dota_oracle_common.utils.set_logging import get_logger

# import main orchestrators for each stage
from .data_fetching.new_match_orchestrator import NewMatchOrchestrator
from .feature_engineering.feature_engineering_orchestrator import FeatureEngineeringOrchestrator
from .prediction.prediction_orchestrator import PredictionOrchestrator
from .completion.completion_orchestrator import CompletionOrchestrator
from .services.notifications_service import NotificationService
from .services.dlq_retry_service import DlqRetryService


logger = get_logger(__name__)


class MatchPipelineOrchestrator:
    """Pipeline for processing live matches, making predictions, and tracking outcomes."""

    def __init__(
        self,
        new_match_orchestrator: NewMatchOrchestrator,
        feature_engineering_orchestrator: FeatureEngineeringOrchestrator,
        prediction_orchestrator: PredictionOrchestrator,
        completion_orchestrator: CompletionOrchestrator,
        notification_service: NotificationService,
        dlq_retry_service: DlqRetryService,
    ):
        self.new_match_orchestrator = new_match_orchestrator
        self.feature_engineering_orchestrator = feature_engineering_orchestrator
        self.prediction_orchestrator = prediction_orchestrator
        self.completion_orchestrator = completion_orchestrator
        self.notification_service = notification_service
        self.dlq_retry_service = dlq_retry_service

    async def run_cycle(self) -> None:
        """Runs one cycle of the live match processing pipeline."""
        try:
            # 0. Retry failed events from previous cycles
            await self.dlq_retry_service.run_retry_sweep()

            # 1. Fetch current matches to identify and onboard new matches
            count_new_matches: int = await self.new_match_orchestrator.run_new_match_cycle()

            # 2. Process matches pending feature engineering
            count_features_engineered: int = await self.feature_engineering_orchestrator.run_feature_engineering_cycle()

            # 3. Process matches pending prediction
            count_predicted: int = await self.prediction_orchestrator.run_prediction_cycle()

            # 4. Process predicted matches to check for completion
            count_completed: int = await self.completion_orchestrator.run_completion_cycle()

            logger.info(
                f"Pipeline cycle stats: "
                f"New={count_new_matches}, "
                f"FE_Processed={count_features_engineered}, "
                f"Predicted={count_predicted}, "
                f"Completed={count_completed}"
            )

            total_counts = count_new_matches + count_features_engineered + count_predicted + count_completed
            if total_counts:
                await self.notification_service.notify_state_change()

        except Exception as e:
            logger.error(f"Error in MatchPipelineOrchestrator run_cycle: {str(e)}", exc_info=True)
            raise
