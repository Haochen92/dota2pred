import bentoml
from bentoml.models import BentoModel
from dota_oracle_common.models.inference import ModelPredictionAPIResponse, PredictionInputPayload
from typing import Dict, Any, List
from dota_oracle_common.utils.set_logging import get_logger

logger = get_logger(__name__)

# configurations
my_image = (
    bentoml.images.Image(python_version="3.11", distro="debian")
    .run('echo "Installing system packages..."')
    .system_packages("curl")
    .python_packages(
        "scikit-learn",
        "numpy",
        "pandas",
        "git+https://github.com/Haochen92/dota2pred.git@dev#subdirectory=packages/dota_oracle_common",
    )
    .run('echo "Image Built Successfully...!"')
)


@bentoml.service(name="dota_prediction_service", image=my_image)
class DotaPredictionService:

    pro_match_model_ref = BentoModel("dota_oracle_pro_match_model:latest")
    pub_match_model_ref = BentoModel("dota_oracle_pub_match_model:latest")

    def __init__(self) -> None:
        """Initializes the service by loading both models into memory."""
        logger.info("Initializing DotaPredictionService...")
        self.pro_model = bentoml.sklearn.load_model(self.pro_match_model_ref)
        self.pub_model = bentoml.sklearn.load_model(self.pub_match_model_ref)
        logger.info("Service initialized successfully with two models.")

    def _predict(self, model, features: List[List[float]]) -> ModelPredictionAPIResponse:
        """Private helper to run prediction and format the output, reducing duplication."""
        try:
            prediction = model.predict(features)
            probability = model.predict_proba(features)[
                :, 1
            ]  # Use numpy col, row selector to extract radiant_win proba only
            return ModelPredictionAPIResponse(prediction=prediction.tolist(), probability=probability.tolist())
        except Exception as e:
            logger.error(f"Prediction failed for model {model}: {e}", exc_info=True)
            raise bentoml.exceptions.InternalServerError(f"Prediction failed: {e}")

    # --- API Endpoints ---

    @bentoml.api(route="/predict/pro")
    def predict_pro_match(self, data: PredictionInputPayload) -> ModelPredictionAPIResponse:
        """Predicts the outcome for a professional match."""
        return self._predict(self.pro_model, data.input_features)

    @bentoml.api(route="/predict/public")
    def predict_pub_match(self, data: PredictionInputPayload) -> ModelPredictionAPIResponse:
        """Predicts the outcome for a public match."""
        return self._predict(self.pub_model, data.input_features)

    @bentoml.api(route="/metadata/pro")
    def get_pro_model_metadata(self) -> Dict[str, Any]:
        """Returns metadata for the professional match model."""
        return self.pro_match_model_ref.info.metadata

    @bentoml.api(route="/metadata/public")
    def get_pub_model_metadata(self) -> Dict[str, Any]:
        """Returns metadata for the public match model."""
        return self.pub_match_model_ref.info.metadata

    @bentoml.api(route="/readyz")
    def is_ready(self) -> str:
        """Health check endpoint."""
        return "OK"
