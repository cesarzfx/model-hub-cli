# service/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException

from ...core.config import get_settings
from ...core.security import hash_password, verify_password, create_jwt, Role
from ... import deps
from ...domain import repos
from ...domain.schemas import LoginRequest, LoginResult  # adjust if your models are in a different module

router = APIRouter()

@router.post("/login", response_model=LoginResult)
def login(
    req: LoginRequest,
    repo: repos.PackageRepo = Depends(deps.get_repo),
):
    user = repo.get_user(req.username)
    if not user or not verify_password(req.password, user["hashed"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_jwt(
        sub=req.username,
        role=Role(user["role"]),
    )
    return LoginResult(token=token)
