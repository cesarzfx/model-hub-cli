# service/app/api/v1/admin.py
from fastapi import APIRouter, Depends
from ...domain import repos
from ...core.security import hash_password
from ... import deps

router = APIRouter()

@router.post("/reset")
def reset(repo: repos.PackageRepo = Depends(deps.get_repo),
          user=Depends(deps.require_admin)):
    repo.reset()
    # recreate default admin
    pwd = "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"
    repo.upsert_user("ece30861defaultadminuser", hash_password(pwd), "admin")
    return {"ok": True}

@router.post("/bootstrap")
def bootstrap(repo: repos.PackageRepo = Depends(deps.get_repo)):
    # Allow seeding ONLY if there are no users yet
    if repo.user_count() > 0:
        return {"ok": False, "note": "already initialized"}
    pwd = "correcthorsebatterystaple123(!__+@**(A;DROP TABLE packages"
    repo.upsert_user("ece30861defaultadminuser", hash_password(pwd), "admin")
    return {"ok": True}
