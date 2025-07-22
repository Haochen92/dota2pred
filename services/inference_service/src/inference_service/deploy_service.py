import bentoml
from bentoml.exceptions import ServiceUnavailable, BentoMLException
from dota_oracle_common.utils.set_logging import get_logger
from inference_service.build_service import build_bento

logger = get_logger(__name__)


def deploy_service(bento: bentoml.Bento) -> None:
    """_summary_

    Deploy bento to Bentoml Cloud

    Args:
        bento (bentoml.Bento): Freshly built bento :)
    """
    try:
        deployment_name = "dota-oracle-predictor"
        bento_tag_name = str(bento.tag)
        dep = bentoml.deployment.create(bento=bento_tag_name, name=deployment_name, strategy="RollingUpdate")
        dep.wait_until_ready(timeout=3600)
        logger.info(f"bento {bento_tag_name} has been successfully deployed to bento cloud as name: {deployment_name}")
    except ServiceUnavailable as se:
        logger.error(f"Deployment timed out or service unable: {se}")
        raise
    except BentoMLException as be:
        logger.error(f"Bentoml deployment error, {be}")
        raise
    except Exception as e:
        logger.error(f"Unexpected deployment error: {e}")
        raise


def main() -> None:
    logger.info("Starting to build and deploy bento to BentoCloud")
    try:
        bento = build_bento()
        deploy_service(bento)
    except Exception as e:
        logger.error(f"Error encountered when deploying bento to cloud: {e}")
        raise


if __name__ == "__main__":
    main()
