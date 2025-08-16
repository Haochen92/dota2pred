from fastapi import APIRouter
from typing import Dict
from dota_oracle_common.utils import get_logger

"""
SSE Endpoint
"""


# Instantiate supporting services
logger = get_logger(__name__)

# Instantiate APIrouter
router = APIRouter(
    prefix="matchtable",
    tags=["matchtable"],
)


@router.get("/matches")
async def get_matches() -> Dict[str, str]:
    return {"message": "Matches endpoint - connect to database via common package"}
