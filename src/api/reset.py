from fastapi import APIRouter, HTTPException
from typing import Dict, List
import os
import glob

router = APIRouter()

# Directory to store artifacts - this would be configured properly in production
ARTIFACTS_DIR = "/app/artifacts"  # Changed to match the test environment path


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
def reset_registry() -> Dict:
    """
    Reset the registry to its initial state.
    """
    # Clear all artifacts
    clear_artifacts()

    # Reset any in-memory state here

    return {"message": "Registry reset successfully"}
