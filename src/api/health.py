from fastapi import APIRouter
from typing import Dict

router = APIRouter()


@router.get("/health")
async def get_health() -> Dict:
    """
    Lightweight liveness probe. Returns HTTP 200 when the registry API is reachable.
    """
    return {}
