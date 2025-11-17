from fastapi import APIRouter, HTTPException
from typing import Dict, List
from pydantic import BaseModel
from loguru import logger
import os

# Ensure logs directory exists and configure Loguru to write to logs/app.log
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../logs"))
os.makedirs(log_dir, exist_ok=True)
log_path = os.path.join(log_dir, "app.log")
logger.add(log_path, rotation="10 MB", retention="10 days")
from starlette.requests import Request

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


async def log_request(request: Request) -> None:
    """Log details of the incoming request."""
    logger.info(f"Endpoint called: {request.url.path}")
    logger.info(f"Request method: {request.method}")
    logger.info(f"Request headers: {request.headers}")
    body = await request.body()
    logger.info(
        f"Request body: {body.decode('utf-8')}" if body else "Request body: None"
    )


async def example_endpoint(request: Request) -> dict:
    await log_request(request)
    # ...existing endpoint logic...
    return {"status": "success"}
