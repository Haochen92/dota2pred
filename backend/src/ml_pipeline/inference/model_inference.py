import aiohttp
import pandas as pd
from typing import List, Union
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from database.schemas.inference import MatchPrediction
from pydantic_models.inference import ModelMetaData

class PredictionService:
    def __init__(self, engine: AsyncEngine, model_url: str = "http://localhost:3333/predict"):
        self.engine = engine
        self.model_url = model_url
        self.prediction_data = []

    async def get_prediction(self, df_inputs: pd.DataFrame) -> Union[int, List[int]]:
        # Extract match_ids
        match_ids = df_inputs['match_id'].tolist()
        
        inputs = df_inputs.drop(columns=['match_id'])
        values = inputs.values.tolist()
        request_data = {"input_data": {"features": values}}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.model_url,
                    headers={"Content-Type": "application/json"},
                    json=request_data
                ) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        # The BentoML API returns {"prediction": [int, int, ...]}
                        predictions = result['prediction']
                        model_metadata = ModelMetaData(**result['metadata'])
                        self.prediction_data = [
                            {
                                "match_id":match_id,
                                "prediction":pred,
                                "metadata":model_metadata
                            } for match_id, pred in zip(match_ids, predictions) 
                        ]
                        return predictions[0] if len(predictions) == 1 else predictions
                    else:
                        print(f"Error: {response.status}")
                        raise ValueError(f"API returned status code {response.status}")
        except Exception as e:
            self.prediction_data = []
            raise e
        


    async def store_prediction_to_db(self):
        if not self.prediction_data:
            raise ValueError("No predictions Available")
        
        async with AsyncSession(self.engine) as session:
            try:
                for item in self.prediction_data:
                    prediction_record = MatchPrediction(
                        match_id=item["match_id"],
                        prediction=item["prediction"],
                        model_name=item["metadata"].model_name,
                        model_version=item["metadata"].model_version
                    )
                    
                    session.add(prediction_record)
                await session.commit()
            
                return True
            except Exception as e:
            # Rollback in case of error
                await session.rollback()
                print(f"Error storing prediction to database: {str(e)}")
                raise e
    
    async def predict_and_store(self, df_inputs: pd.DataFrame) -> Union[int, List[int]]:
        """Combined method to get predictions and store them in one operation"""
        prediction_data = await self.get_prediction(df_inputs)
        await self.store_prediction_to_db()
        return prediction_data