# service/app/api/v1/admin.py
import os
from fastapi import APIRouter
from ...core.security import hash_password
from ...domain import repos

router = APIRouter()

DEFAULT_ADMIN_USER = "ece30861defaultadminuser"
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "ChangeMe!123")  # <= 72 chars

@router.post("/bootstrap")
def bootstrap():
    repo = repos.get_repo()
    if repo.get_user(DEFAULT_ADMIN_USER):
        return {"detail": "already-initialized"}
    repo.upsert_user(DEFAULT_ADMIN_USER, hash_password(DEFAULT_ADMIN_PASS), "admin")
    return {"detail": "initialized"}
