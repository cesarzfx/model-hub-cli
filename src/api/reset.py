from fastapi import APIRouter
from typing import Dict
from pathlib import Path
import os
import shutil
import logging

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
def reset_registry() -> Dict[str, str]:
    """
    Reset registry state for the autograder.
    """
    clear_artifacts()

    return {"message": "Registry reset successfully"}
