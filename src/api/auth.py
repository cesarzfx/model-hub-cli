from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Optional
import time
import secrets
import hashlib
import binascii

router = APIRouter()


class User(BaseModel):
    """
    Minimal user identity record carried inside tokens.
    """

    name: str
    is_admin: bool


class UserAuthenticationInfo(BaseModel):
    """
    Secret material supplied by the client when authenticating.
    """

    password: str


class AuthenticationRequest(BaseModel):
    """
    Matches the OpenAPI AuthenticationRequest schema
    """

    user: User
    secret: UserAuthenticationInfo


# Tokens are valid for 10 hours OR 1000 successful uses, whichever comes first.
TOKEN_TTL_SECONDS = 10 * 60 * 60  # 10 hours
TOKEN_MAX_USES = 1000

issued_tokens: Dict[str, Dict] = {}

DEFAULT_ADMIN_USERNAME = "ece30861defaultadminuser"
DEFAULT_ADMIN_IS_ADMIN = True

# PBKDF2 parameters – strong enough for this project and deterministic so that
# the autograder can authenticate with the known example password.
_PBKDF2_SALT = b"ece30861-salt"
_PBKDF2_ITERS = 100_000

# This hash was computed as:
#   hashlib.pbkdf2_hmac(
#       "sha256",
#       b"correcthorsebatterystaple123(!__+@**(A'\"`;DROP TABLE artifacts;",
#       b"ece30861-salt",
#       100_000,
#   ).hex()
_DEFAULT_ADMIN_PASSWORD_HASH = (
    "8e8ecae2e01c7a30c9dea215e512d091dc80653fd3182caa0991a53c4ab726ce"
)


def _hash_password(password: str) -> str:
    """
    Derive a salted PBKDF2-HMAC-SHA256 hash of the given password.
    """
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _PBKDF2_SALT,
        _PBKDF2_ITERS,
    )
    return binascii.hexlify(dk).decode("ascii")


def _verify_password(expected_hash: str, candidate: str) -> bool:
    """
    Constant-time-ish comparison of a candidate password to an expected hash.
    """
    candidate_hash = _hash_password(candidate)
    # Use secrets.compare_digest to avoid timing side channels.
    return secrets.compare_digest(expected_hash, candidate_hash)


def _generate_token() -> str:
    """
    Generate a cryptographically strong opaque bearer token.
    """
    # We prefix with "bearer " so that the example in the OpenAPI spec is valid.
    return "bearer " + secrets.token_urlsafe(32)


def _now() -> float:
    return time.time()


# Simple in-memory user "database". In a real system this would be a persistent
# store with a unique salt per user, but this is sufficient for the assignment.
_users: Dict[str, Dict[str, object]] = {
    DEFAULT_ADMIN_USERNAME: {
        "record": User(name=DEFAULT_ADMIN_USERNAME, is_admin=DEFAULT_ADMIN_IS_ADMIN),
        "password_hash": _DEFAULT_ADMIN_PASSWORD_HASH,
    }
}


# ---------------------------------------------------------------------------
# Helper functions for other modules (optional to use)
# ---------------------------------------------------------------------------


def is_token_valid(token: str) -> bool:
    """
    Lightweight check that a token exists, has not expired, and still has
    remaining uses. Does NOT consume a use.
    """
    info = issued_tokens.get(token)
    if not info:
        return False
    if info["expires_at"] <= _now():
        return False
    if info["remaining_uses"] <= 0:
        return False
    return True


def consume_token(token: str) -> User:
    """
    Validate and consume a single use of a token.

    Returns the associated User on success or raises HTTPException(401)
    if the token is missing, expired, or exhausted.
    """
    info = issued_tokens.get(token)
    if not info:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")

    if info["expires_at"] <= _now():
        # Expired – clean up and reject.
        issued_tokens.pop(token, None)
        raise HTTPException(status_code=401, detail="Token has expired.")

    if info["remaining_uses"] <= 0:
        issued_tokens.pop(token, None)
        raise HTTPException(status_code=401, detail="Token usage limit exceeded.")

    info["remaining_uses"] -= 1
    return info["user"]


def require_token(
    x_authorization: Optional[str] = Header(default=None, alias="X-Authorization"),
) -> User:
    """
    FastAPI dependency helper:
    """
    if not x_authorization:
        raise HTTPException(status_code=401, detail="X-Authorization header required.")
    return consume_token(x_authorization)


# ---------------------------------------------------------------------------
# /authenticate endpoint
# ---------------------------------------------------------------------------


@router.put("/authenticate", response_model=str, operation_id="CreateAuthToken")
def authenticate(auth_request: AuthenticationRequest) -> str:
    """
    Authenticate this user and return an access token.

    Behavior matches the non-baseline /authenticate spec:

    - Request body: AuthenticationRequest (user + secret.password)
    - 200: returns AuthenticationToken (string) on valid credentials
    - 400: reserved for malformed payloads (Pydantic/validation errors will
           normally be returned as 422 by FastAPI)
    - 401: invalid username or password
    - Multiple simultaneous tokens per user are allowed.
    - Each token expires after 10 hours OR 1000 uses.
    """

    user_in = auth_request.user
    secret_in = auth_request.secret

    # Look up user.
    stored = _users.get(user_in.name)
    if not stored:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    stored_user: User = stored["record"]  # type: ignore[assignment]
    stored_hash: str = stored["password_hash"]  # type: ignore[assignment]

    # For the default admin account we also enforce that the caller is asking
    # for admin access (is_admin = True), matching the example in the spec.
    if stored_user.is_admin and not user_in.is_admin:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # Verify the password securely.
    if not _verify_password(stored_hash, secret_in.password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    # At this point credentials are valid – issue a fresh token.
    token = _generate_token()
    issued_tokens[token] = {
        "user": stored_user,
        "expires_at": _now() + TOKEN_TTL_SECONDS,
        "remaining_uses": TOKEN_MAX_USES,
    }

    return token
