from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List
import os

router = APIRouter()

class SystemHealth(BaseModel):
    status: str
    uptime: float
    version: str

class SystemTracks(BaseModel):
    plannedTracks: List[str]

_system_start_time = None

def get_system_health() -> SystemHealth:
    global _system_start_time
    if not _system_start_time:
        _system_start_time = os.times()
    
    return SystemHealth(
        status="active",
        uptime=os.times()[4] - _system_start_time[4],
        version="1.0.0"
    )

@router.get("/health")
def health_check() -> Dict:
    """
    Get system health status
    """
    return get_system_health().dict()

@router.get("/tracks")
def get_tracks() -> Dict:
    """
    Get the list of tracks being implemented
    """
    return SystemTracks(
        plannedTracks=[
            "System Health Track",
            "Access Control Track",
            "Reset Track"
        ]
    ).dict()