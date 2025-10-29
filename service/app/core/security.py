# service/app/core/security.py
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
import jwt
from typing import Literal
from .config import get_settings

# password hashing context
pwd_context = CryptContext(
    schemes=["argon2"], 
    deprecated="auto"
)

Role = Literal["admin", "contributor", "viewer"]

def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given password."""
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(password, hashed)

def create_jwt(*, subject: str, role: Role) -> str:
    """Generate a signed JWT for a user."""
    s = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=s.JWT_EXPIRE_HOURS)
    payload = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": s.JWT_ISSUER,
        "aud": s.JWT_AUDIENCE,
        "max_calls": s.JWT_MAX_CALLS,
    }
    return jwt.encode(payload, s.JWT_SECRET, algorithm="HS256")

def decode_jwt(token: str) -> dict:
    """Verify and decode a JWT."""
    s = get_settings()
    return jwt.decode(
        token,
        s.JWT_SECRET,
        algorithms=["HS256"],
        audience=s.JWT_AUDIENCE,
        issuer=s.JWT_ISSUER,
        options={
            "require": ["exp", "iss", "aud", "sub"],
            "verify_signature": True,
            "verify_aud": True,
            "verify_iss": True,
        },
    )
