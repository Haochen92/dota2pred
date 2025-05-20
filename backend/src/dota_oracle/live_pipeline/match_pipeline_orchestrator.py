# import logging
from dota_oracle.utils.set_logging import get_logger

# import main orchestrators for each stage
from .new_match_orchestrator import NewMatchOrchestrator
from .feature_engineering_orchestrator import FeatureEngineeringOrchestrator
from .prediction_orchestrator import PredictionOrchestrator
from .completion_orchestrator import CompletionOrchestrator 



logger = get_logger(__name__)

class MatchPipelineOrchestrator:
    """Pipeline for processing live matches, making predictions, and tracking outcomes."""

    def __init__(
        self,
        new_match_orchestrator: NewMatchOrchestrator,
        feature_engineering_orchestrator: FeatureEngineeringOrchestrator, 
        prediction_orchestrator: PredictionOrchestrator,           
        completion_orchestrator: CompletionOrchestrator         
    ):
        self.new_match_orchestrator = new_match_orchestrator
        self.feature_engineering_orchestrator = feature_engineering_orchestrator
        self.prediction_orchestrator = prediction_orchestrator
        self.completion_orchestrator = completion_orchestrator

    async def run_cycle(self) -> None:
        """Runs one cycle of the live match processing pipeline."""
        try:
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

        except Exception as e:
            logger.error(f"Error in MatchPipelineOrchestrator run_cycle: {str(e)}", exc_info=True)
            # continue next cycle on failure