import requests
import json

def get_prediction(df_inputs):
    inputs = df_inputs.drop(columns=['match_id'])
    values = inputs.values.tolist()
    request_data = {"input_data": {"features": [values]}}
    try:
        res = requests.post(
            "http://localhost:3333/predict",
            headers={"Content-Type": "application/json"},
            data=json.dumps(request_data)
        )
        
        if res.status_code == 200:
            result = res.json()
            output = result['prediction'][0]
        else:
            print(f"Error: {res.status_code}")
    except Exception as e:
        raise(e)
    
    return output