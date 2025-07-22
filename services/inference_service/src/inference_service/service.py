import bentoml
from bentoml.models import BentoModel
from dota_oracle_common.models.inference import ModelPredictionAPIResponse
from typing import Dict, Any
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


@bentoml.service(name="match_prediction", image=my_image)
class MatchPredictionService:

    rf_model = BentoModel("dota_oracle_random_forest:latest")  # bentoml use this tag to load the saved model

    def __init__(self) -> None:
        self.model = bentoml.sklearn.load_model(self.rf_model)
        self.model_metadata = self.rf_model.info.metadata

    @bentoml.api  # type: ignore[misc]
    def predict(self, input_data: Dict[str, Any]) -> ModelPredictionAPIResponse:

        features = input_data.get("input_features", {})

        if not features:
            logger.error("No input features provided")
            raise ValueError("Cannot make prediction: no input features provided")

        if not isinstance(features, list):
            raise ValueError(f"input features is {type(features)} but list is required")

        try:
            prediction = self.model.predict(features)
            output = ModelPredictionAPIResponse(prediction=prediction.tolist())
            return output

        except Exception as e:
            logger.error(f"prediction failed, {e}", exc_info=True)
            raise bentoml.exceptions.InternalServerError(f"Prediction failed: {e}")

    @bentoml.api  # type: ignore[misc]
    def get_metadata(self) -> Dict[str, Any]:
        metadata: Dict[str, Any] = self.model_metadata
        return metadata

    @bentoml.api(route="/readyz")  # type: ignore[misc]
    def is_ready(self) -> str:
        return "OK"
