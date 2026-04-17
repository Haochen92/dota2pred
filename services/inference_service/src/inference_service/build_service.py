import bentoml
from dota_oracle_common.utils.set_logging import get_logger
from typing import Any

logger = get_logger(__name__)


def build_bento() -> bentoml.Bento:
    """_summary_
    Builds a Bento, which is a standardized, versioned blueprint of the ML service.

    Returns:
        bentoml.Bento: _description_
    """
    logger.info("building bento... ")
    try:
        bento = bentoml.build(
            service="service:DotaPredictionService",  # reference the file:class
        )
        print(f"{bento} has been successfully created")
        return bento
    except Exception as e:
        print(f"failed to build bento, error: {e}")
        raise


def containerize_bento(bento: bentoml.Bento) -> Any:
    """
    Build a docker image using a Bento
    """
    logger.info("Building containerized environment for bento...")
    try:
        container = bentoml.container.build(
            bento_tag=str(bento.tag), image_tag=("dota_prediction_service:latest",)
        )  # tuple
        print(f"Container for {bento.tag} built successfully")
        return container
    except Exception as e:
        print(f"failed to create container for bento {bento}: {e}")
        raise


def main() -> None:
    try:
        bento = build_bento()
        containerize_bento(bento)
        logger.info("Build process complete")
    except Exception as e:
        err_msg = f"Build process failed, error: {e}"
        logger.error(err_msg, exc_info=True)
        raise e


if __name__ == "__main__":
    main()
