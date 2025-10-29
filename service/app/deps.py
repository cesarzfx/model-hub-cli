# service/app/deps.py
from __future__ import annotations
from typing import Any, Dict

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .core.security import decode_jwt, Role
from .core.config import get_settings                # ✅ ADD THIS
from .domain import repos, storage                   # ✅ ensure this line exists


def get_repo() -> repos.PackageRepo:
    return repos.get_repo()

def get_blob_store() -> storage.BlobStore:
    return storage.get_blob_store()

def auth_header(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return authorization.split(" ", 1)[1]

def require_role(role: Role):
    def dep(token: str = Depends(auth_header)):
        settings = get_settings()
        try:
            payload = decode_jwt(token, settings.JWT_SECRET, settings.JWT_AUDIENCE)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid token")
        if payload.get("role") not in ("viewer", "contributor", "admin"):
            raise HTTPException(status_code=403, detail="Unauthorized role")
        if role == "contributor" and payload["role"] not in ("contributor", "admin"):
            raise HTTPException(status_code=403, detail="Contributor required")
        if role == "admin" and payload["role"] != "admin":
            raise HTTPException(status_code=403, detail="Admin required")
        # optional: decrement calls_left in a token session store
        return payload
    return dep

require_viewer = require_role("viewer")
require_contributor = require_role("contributor")
require_admin = require_role("admin")
