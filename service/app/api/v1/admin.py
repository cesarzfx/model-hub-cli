# service/app/api/v1/admin.py
import os
from fastapi import APIRouter, Depends
from ...core.security import hash_password
from ...domain import repos
from ... import deps

router = APIRouter()

DEFAULT_ADMIN_USER = "ece30861defaultadminuser"
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "ChangeMe!123")  # <= 72 chars

@router.post("/bootstrap")
def bootstrap(repo: repos.PackageRepo = Depends(deps.get_repo)):
    if repo.get_user(DEFAULT_ADMIN_USER):
        return {"detail": "already-initialized"}
    repo.upsert_user(DEFAULT_ADMIN_USER, hash_password(DEFAULT_ADMIN_PASS), "admin")
    return {"detail": "initialized"}

@router.post("/reset")
def reset(repo: repos.PackageRepo = Depends(deps.get_repo), user=Depends(deps.require_admin)):
    """
    Reset the database by deleting all packages and users (except admin).
    Used by autograder to clean state between test runs.
    """
    repo.reset()
    # Re-create admin user after reset
    repo.upsert_user(DEFAULT_ADMIN_USER, hash_password(DEFAULT_ADMIN_PASS), "admin")
    return {"detail": "reset complete"}
