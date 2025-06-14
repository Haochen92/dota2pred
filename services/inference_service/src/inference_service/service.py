import bentoml 
from bentoml.models import BentoModel
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# configurations
my_image = bentoml.images.Image(python_version='3.11', distro='debian') \
    .run('echo "Installing system packages..."') \
    .system_packages('curl') \
    .requirements_file('requirements.txt') \
    .run('echo "Image Built Successfully...!"')

@bentoml.service(name='match_prediction', image=my_image)
class MatchPredictionService:
    
    rf_model = BentoModel('rf_model:latest') # bentoml use this tag to load the saved model
    
    def __init__(self):
        self.model = bentoml.sklearn.load_model(self.rf_model)
        self.model_metadata = self.rf_model.info.metadata
        
    @bentoml.api
    def predict(self, input_data: Dict[str, Any]) -> List:
        
        
        features = input_data.get('input_features', {})
        
        if not features:
            logger.error("No input features provided")
            raise ValueError("Cannot make prediction: no input features provided")
        
        if not isinstance(features, list):
            raise ValueError(f"input features is {type(features)} but list is required")
        
        try:
            prediction = self.model.predict(features)
            return prediction.tolist()
        
        except Exception as e:
            logger.error(f"prediction failed, {e}", exc_info=True)
            raise bentoml.exceptions.InternalServerError(f"Prediction failed: {e}")
    
    @bentoml.api
    def get_metadata(self) -> Dict[str, Any]:
        return self.model_metadata
    
    
    @bentoml.api(route='/readyz')
    def is_ready(self) -> str:
        return "OK"


