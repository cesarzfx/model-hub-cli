from fastapi import APIRouter, HTTPException, Header
from typing import Dict, List
import os
import glob

router = APIRouter()

# Import issued_tokens from auth.py
try:
    from .auth import issued_tokens
except ImportError:
    issued_tokens = {}

# Directory to store artifacts - use local writable directory for testing
ARTIFACTS_DIR = "./artifacts"


def clear_artifacts() -> None:
    """Clear all stored artifacts and recreate empty directory"""
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

    # Ensure artifacts directory exists after reset
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)


@router.delete("/reset")
def reset_registry(X_Authorization: str = Header(...)) -> Dict:
    """
    Reset the registry to its initial state. Requires valid X-Authorization token.
    """
    # Check for token
    if not X_Authorization:
        raise HTTPException(
            status_code=401, detail="You do not have permission to reset the registry."
        )
    if X_Authorization not in issued_tokens:
        raise HTTPException(
            status_code=403,
            detail="Authentication failed due to invalid or missing AuthenticationToken.",
        )

    # Clear all artifacts
    clear_artifacts()

    # Reset any in-memory state here

    return {"message": "Registry reset successfully"}
