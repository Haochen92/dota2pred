from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Dict, Any

app = FastAPI(title="Dota Oracle API Gateway", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.post("/predict")
async def predict(data: Dict[str, Any]):
    async with httpx.AsyncClient() as client:
        response = await client.post("http://prediction-service:3000/predict", json=data)
        return response.json()


@app.get("/matches")
async def get_matches():
    return {"message": "Matches endpoint - connect to database via common package"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
