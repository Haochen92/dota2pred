import bentoml 
from bentoml.models import BentoModel
import numpy as np
from typing import Dict, Any

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
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        
        features = np.array(input_data["features"])
        
        prediction = self.model.predict(features)
        
        return {
            "prediction": prediction.tolist(),
            "metadata": self.model_metadata
        }
    


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