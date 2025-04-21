import aiohttp
from typing import List

async def get_prediction(df_inputs) -> List[int]:
    inputs = df_inputs.drop(columns=['match_id'])
    values = inputs.values.tolist()
    request_data = {"input_data": {"features": [values]}}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://localhost:3333/predict",
                headers={"Content-Type": "application/json"},
                json=request_data
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    # The BentoML API returns {"prediction": [int, int, ...]}
                    output = result['prediction']
                else:
                    print(f"Error: {response.status}")
                    raise ValueError(f"API returned status code {response.status}")
    except Exception as e:
        raise e
    
    return output