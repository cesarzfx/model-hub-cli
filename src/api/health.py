from fastapi import APIRouter, HTTPException
from typing import Dict, List
from pydantic import BaseModel

router = APIRouter()


class TracksResponse(BaseModel):
    plannedTracks: List[str]


@router.get("/health")
async def get_health() -> Dict:
    """
    Lightweight liveness probe. Returns HTTP 200 when the registry API is reachable.
    """
    return {}


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
        # Return the planned tracks
        # Make sure to include all tracks you plan to implement
        return TracksResponse(plannedTracks=["Performance track"])
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="The system encountered an error while retrieving the student's track information",
        )
