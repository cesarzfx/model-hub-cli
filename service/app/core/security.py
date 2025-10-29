# service/app/core/security.py
from __future__ import annotations
from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import jwt  # PyJWT
from passlib.context import CryptContext

from .config import get_settings   # ✅ correct: only import get_settings from .config

# ---- Password hashing (PBKDF2; no 72-byte limit like bcrypt) ----
_pwd = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

def hash_password(pw: str) -> str:
    return _pwd.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return _pwd.verify(pw, hashed)

# ---- Roles ----
class Role(str, Enum):
    viewer = "viewer"
    contributor = "contributor"
    admin = "admin"

# ---- JWT helpers ----
def create_jwt(sub: str, role: Role, max_calls: int | None = None) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=int(s.JWT_EXPIRE_HOURS))
    claims: Dict[str, Any] = {
        "sub": sub,
        "role": role.value,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": s.JWT_ISSUER,       # ✅ issuer
        "aud": s.JWT_AUDIENCE,     # ✅ audience
        "max_calls": int(max_calls if max_calls is not None else s.JWT_MAX_CALLS),
    }
    return jwt.encode(claims, s.JWT_SECRET, algorithm="HS256")


def decode_jwt(token: str) -> Dict[str, Any]:
    s = get_settings()
    return jwt.decode(
        token,
        s.JWT_SECRET,
        algorithms=["HS256"],
        audience=s.JWT_AUDIENCE,
        issuer=s.JWT_ISSUER,
    )
