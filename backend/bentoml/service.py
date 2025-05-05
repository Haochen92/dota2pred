import bentoml 
from bentoml.models import BentoModel
import numpy as np
from typing import Dict, Any, List
from utils.set_logging import get_logger
import subprocess

logger = get_logger(__name__)

# configurations
my_image = bentoml.images.Image(python_version='3.10', distro='debian') \
    .run('echo "Installing system packages..."') \
    .system_packages('curl') \
    .requirements_file('requirements.txt') \
    .run('echo "Image Built Successfully...!"')

@bentoml.service(name='match_prediction', image=my_image)
class MatchPredictionService:
    
    rf_model = BentoModel('rf_model:latest')
    
    def __init__(self):
        self.model = bentoml.sklearn.load_model(self.rf_model)
        self.model_metadata = self.rf_model.info.metadata
        
    @bentoml.api
    def predict(self, input_data: Dict[str, Any]) -> List[Any]:
        
        
        features = input_data.get('input_features', {})
        
        if not features:
            logger.warning("input data is empty")
        
        if not isinstance(features, list):
            raise ValueError(f"input features is {type(features)} but list is required")
        
        try:
            prediction = self.model.predict(features)
            return prediction.tolist()
        
        except Exception as e:
            logger.error(f"prediction failed, {e}", exec_info=True)
            raise bentoml.exceptions.InternalServerError(f"Prediction failed: {e}")
    
    @bentoml.api
    def get_metadata(self) -> Dict[str, Any]:
        return self.model_metadata


if __name__ == "__main__":
    try:
        bento = bentoml.build(
        service='match_prediction',
        )
        print(f'{bento} has been successfully created')
    except Exception as e:
        print(f'failed to build bento, error: {e}')
        
    try:
        container  = bentoml.container.build(
            bento_tag=str(bento.tag),
            image_tag=('match_prediction:latest',)
        )
        print(f'Container for {bento.tag} built successfully')
    except Exception as e:
        print(f'failed to create container for bento {bento}: {e}')
        
    try:
        subprocess.run(
            command=[
                'docker_compose',
                'up',
                '-d',
                '--force-recreate',
                '--no-deps',
                'bentoml'
            ]
        )
    except Exception as e:
        logger.error(f'Error encountered while rebuidling bentoml service')
        