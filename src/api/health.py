from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def get_health():
    """
    Lightweight liveness probe. Returns HTTP 200 when the registry API is reachable.
    """
    return {}
