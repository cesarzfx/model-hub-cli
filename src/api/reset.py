from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from pathlib import Path
import os
import shutil
import logging

from .auth import require_token, User

router = APIRouter()

# Use the same env var / default as the rest of the app
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "/tmp/artifacts"))


def clear_artifacts() -> None:
    """
    Best-effort cleanup of local artifact storage.
    """
    try:
        if not ARTIFACTS_DIR.exists():
            ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
            return

        for child in ARTIFACTS_DIR.iterdir():
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
            except Exception:
                # Log but do NOT fail the reset endpoint
                logging.exception("Error while removing artifact entry: %s", child)

    except Exception:
        # Final safety net – never let errors escape to FastAPI
        logging.exception("Error while clearing artifacts directory: %s", ARTIFACTS_DIR)


@router.delete("/reset")
def reset_registry(user: User = Depends(require_token)) -> Dict[str, str]:
    """
    Reset registry state for the autograder.
    Requires authentication via X-Authorization header.
    Only admin users can reset the registry.
    """
    # Require admin privileges
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required to reset registry"
        )
    
    clear_artifacts()

    return {"message": "Registry reset successfully"}
