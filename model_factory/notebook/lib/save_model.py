import os
import bentoml
from dota_oracle_common.utils.set_logging import get_logger
from joblib import load
from dota_oracle_common.models.inference.schema import VersionMetaData, PerformanceMetrics, ModelMetaData
from dota_oracle_common.models.features import AllFeaturesDTO
from datetime import datetime as dt

logger = get_logger(__name__)


def load_model_from_dir():
    model_dir = "models/"
    model_path = os.path.join(model_dir, "random_forest_model.joblib")
    model = load(model_path)
    return model


def save_sklearn_model(model, model_name: str, metadata: ModelMetaData):
    logger.info(f"attempting to save model {model_name}")
    saved_model = bentoml.sklearn.save_model(
        name=model_name, model=model, signatures={"predict": {"batchable": True}}, metadata=metadata.model_dump()
    )

    logger.info(f"Model saved: {saved_model}")


def load_and_save_model(model_name: str = "model"):
    model = load_model_from_dir()

    feature_columns = list(AllFeaturesDTO.model_fields.keys())

    performance = PerformanceMetrics(accuracy=0.57)

    version_data = VersionMetaData(performance_metrics=performance, feature_columns=feature_columns)

    metadata = ModelMetaData(name=model_name, version="0.0.1", trained_date=dt.now(), version_metadata=version_data)

    save_sklearn_model(model=model, model_name=model_name, metadata=metadata)
    print("process complete")


if __name__ == "__main__":
    load_and_save_model()
