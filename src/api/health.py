from fastapi import APIRouter, HTTPException
from typing import Dict, List
from pydantic import BaseModel
from loguru import logger

router = APIRouter()


class TracksResponse(BaseModel):
    plannedTracks: List[str]  # Updated to camelCase to match the OpenAPI spec


@router.get("/health")
async def get_health() -> Dict:
    """
    Lightweight liveness probe. Returns HTTP 200 when the registry API is reachable.
    """
    return {"description": "Service reachable."}


@router.get(
    "/tracks",
    response_model=TracksResponse,
    responses={
        200: {
            "description": "Return the list of tracks the student plans to implement"
        },
        500: {
            "description": "The system encountered an error while retrieving the student's track information"
        },
    },
)
async def get_tracks() -> TracksResponse:
    """
    Get the list of tracks a student has planned to implement in their code.
    """
    try:
        # Return the planned tracks as per the updated request
        return TracksResponse(plannedTracks=["Access control track"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="The system encountered an error while retrieving the student's track information",
        )


def log_request(request):
    """Log details of the incoming request."""
    logger.info(f"Endpoint called: {request.path}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    logger.info(f"Request body: {request.get_data(as_text=True)}")


# Example usage in an endpoint
def example_endpoint(request):
    log_request(request)
    # ...existing endpoint logic...
    return {"status": "success"}
