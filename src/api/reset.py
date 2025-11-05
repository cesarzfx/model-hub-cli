from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
import os
import glob
from src.api.auth import verify_token, User

router = APIRouter()

# Directory to store artifacts - this would be configured properly in production
ARTIFACTS_DIR = "/tmp/artifacts"

def clear_artifacts() -> None:
    """Clear all stored artifacts"""
    if os.path.exists(ARTIFACTS_DIR):
        files = glob.glob(f"{ARTIFACTS_DIR}/*")
        for f in files:
            try:
                if os.path.isdir(f):
                    os.rmdir(f)
                else:
                    os.remove(f)
            except Exception as e:
                print(f"Error removing {f}: {e}")

@router.delete("/reset")
def reset_registry(user: User = Depends(verify_token)) -> Dict:
    """
    Reset the registry to its initial state.
    Requires admin privileges.
    """
    if not user.is_admin:
        raise HTTPException(status_code=401, detail="Admin privileges required")
    
    # Clear all artifacts
    clear_artifacts()
    
    # Reset any in-memory state here
    
    return {"message": "Registry reset successfully"}
