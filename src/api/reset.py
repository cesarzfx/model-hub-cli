from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.delete("/reset")
def reset_registry():
    raise HTTPException(status_code=501, detail="Not implemented")
