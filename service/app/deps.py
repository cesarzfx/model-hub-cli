# service/app/deps.py
from __future__ import annotations
from typing import Any, Dict

from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .core.security import decode_jwt, Role
# get_settings not needed here unless you use it elsewhere             
from .domain import repos, storage                   


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
        try:
           payload = decode_jwt(token)
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
# service/app/deps.py
# ... existing imports and helpers ...

# already have: require_viewer / require_contributor / require_admin
# Add this alias so auth.py can depend on it:
def require_any_role(token: str = Depends(auth_header)):
    # same behavior as require_viewer: any valid token w/ role in {"viewer","contributor","admin"}
    return require_viewer(token)  # simple reuse


require_viewer = require_role("viewer")
require_contributor = require_role("contributor")
require_admin = require_role("admin")
"""
Convenience dependency that accepts any authenticated user role.
Equivalent to requiring at least a 'viewer' role.
"""
require_any_role = require_viewer
