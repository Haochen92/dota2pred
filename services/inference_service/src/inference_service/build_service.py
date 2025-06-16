import bentoml 
import logging

logger = logging.getLogger(__name__)

def build_bento() -> bentoml.Bento:
    """_summary_
    Builds a Bento, which is a standardized, versioned blueprint of the ML service.
    
    Returns:
        bentoml.Bento: _description_
    """
    logger.info("building bento... ")
    try:
        bento = bentoml.build(
        service='service:MatchPredictionService', # reference the file:class
        )
        print(f'{bento} has been successfully created')
        return bento
    except Exception as e:
        print(f'failed to build bento, error: {e}')
        raise

def containerize_bento(bento: bentoml.Bento):
    """
    Build a docker image using a Bento
    """
    logger.info("Building containerized environment for bento...")
    try:
        container = bentoml.container.build(
            bento_tag=str(bento.tag),
            image_tag=('match_prediction:latest',) # tuple
        )
        print(f'Container for {bento.tag} built successfully')
        return container
    except Exception as e:
        print(f'failed to create container for bento {bento}: {e}')
        raise
    
def main():
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
