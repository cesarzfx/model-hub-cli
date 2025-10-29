# service/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException

from ...core.config import get_settings
from ...core.security import verify_password, create_jwt, Role
from ... import deps
from ...domain import repos
from ...domain.schemas import LoginRequest, LoginResult  # adjust if your models are in a different module

router = APIRouter()

@router.post("/login", response_model=LoginResult)
def login(req: LoginRequest, repo: repos.PackageRepo = Depends(deps.get_repo)):
    user = repo.get_user(req.username)
    if not user or not verify_password(req.password, user["hashed"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt(subject=req.username, role=user["role"])  # ✅ correct param names
    return LoginResult(token=token)

@router.get("/whoami")
def whoami(claims = Depends(deps.require_any_role)):  # or deps.require_viewer
    return claims