# service/app/api/v1/health.py
import time
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
_started = time.time()
_errors = 0
_success = 0

class Health(BaseModel):
    uptime_s: float
    success: int
    errors: int
    recent_warnings: list[str] = []

@router.get("", response_model=Health)
def health():
    return Health(uptime_s=time.time() - _started, success=_success, errors=_errors, recent_warnings=[])
